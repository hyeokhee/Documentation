import base64
import json
import numpy as np
import os
import pathlib
from pathlib import Path
import re
from shutil import rmtree
from urllib.request import urlopen
from json import dumps
from _code_generation_helpers import get_type, to_key, INDICATORS

TAG = f'<!-- Code generated by {os.path.basename(__file__)} -->'
OPTION_INDICATORS = ["ImpliedVolatility", "Delta", "Gamma", "Vega", "Theta", "Rho"]

def _generate_landing_page(start: int, stop: int, path: str, heading: str, content:str) -> None:
    landing = {
        'type' : 'landing',
        'heading' : heading,
        'subHeading' : '',
        'content' : content,
        'alsoLinks' : [],
        'featureShortDescription': {f'{n:02}': '' for n in range(start, stop)}
    }
    with open(f'{path}/00.json', 'w', encoding='utf-8') as fp:
        fp.write(dumps(landing, indent=4))

def _format_introduction(type_name: str, text: str) -> str:
    if 'CandlestickPatterns' in type_name:
        return f"Create a new {text} to indicate the pattern's presence."

    text = text.replace("Represents", "This indicator represents")
    if "Source: " in text:
        link_split = text.split("http")
        return link_split[0].replace("Source: ", f'<sup><a href="https{link_split[1]}">source</a></sup>'.replace("httpss", "https"))
    return text

PROPERTIES_EXCEPTIONS = ['MovingAverageType', 'IsReady', 'WarmUpPeriod', 'Name', 'Period', 'Samples', 
                'Current', "Consolidators", "Previous", "Window", "[System.Int32]"]

def _extract_properties(properties: list):
    numerical_properties = ''
    indicator_properties = ''
    for property in properties:
        property_name = property["property-name"]
        if property_name in PROPERTIES_EXCEPTIONS:
            continue
        # Some properties are lists we cannot plot
        full_type = property['property-full-type-name'] 
        if full_type.startswith('System.Collection'):
            continue
        if full_type.startswith('QuantConnect'):
            indicator_properties += f'"{property_name}",'
        else:
            numerical_properties += f'"{property_name}",'

    return f'array({indicator_properties[:-1]})', f'array({numerical_properties[:-1]})'

def _get_helpers():
    with open(f'Resources/indicators/IndicatorImageGenerator.py', mode='r') as fp:
        lines = fp.readlines()
        helpers = {}
        for i, line in enumerate(lines):
            if 'title' in line and ':' in line:
                name = lines[i-3].split(':')[0].strip()[1:-1]
                full_constructor = lines[i-1]
                parts = line.split('(')

                helpers[to_key(name)] = {
                    'method': parts[0].split(' ')[-1][1:], 
                    'arguments': ')'.join('('.join(parts[1:]).split(')')[:-1]),
                    'constructor-arguments': ')'.join('('.join(full_constructor.split('(')[1:]).split(')')[:-1])
                }

        return helpers

def _get_image_source(folder: str) -> str:
    image = '/'.join([part[3:].strip().lower().replace(' ','-') for part in folder.parts])
    return f'https://cdn.quantconnect.com/docs/i/{image}.png'

def _replace_last_occurrence(string, old_substring, new_substring):
    last_index = string.rfind(old_substring)
    if last_index != -1:
        return string[:last_index] + new_substring + string[last_index + len(old_substring):]
    else:
        return string

def Generate_Indicators_Reference():
    indicators = dict()
    helpers = _get_helpers()

    path = Path('Resources/indicators/constructors')
    for file in path.iterdir():
                
        with open(file, mode='r') as fp:
            content = fp.read()
            start = content.find('QuantConnect')
            type_name = content[start: content.find('(', start)].strip()
            
            indicator = get_type(type_name)
            key = " ".join(re.findall('[a-zA-Z][^A-Z]*', indicator['type-name']))
            indicator['description'] = _format_introduction(type_name, indicator.get('description'))

            start = content.find('https://github.com/QuantConnect/Lean/blob/master/Indicators/')   
            indicator['source'] = content[start: 3 + content.find('.cs', start)].strip()

            helper = helpers.get(file.stem, {
                'method': indicator['type-name'], 
                'arguments': "symbol",
                'constructor-arguments': None
            } )

            arguments = helper['arguments']
            indicator['helper-name'] = helper['method'] 
            indicator['helper-arguments'] = arguments
            start = arguments.find(',')
            if start > 0:
                arguments = arguments[1 + start:].strip()
            indicator['constructor-arguments'] = helper['constructor-arguments']
            indicator['has-moving-average-type-parameter'] = 'MovingAverageType' in content
            indicator['properties'] = _extract_properties(indicator['properties'])

            indicators[key] = indicator

    types = {
        'Indicator': {
            'name': 'data-point-indicator',
            'update-parameter-type': 'time/number pair or an <code>IndicatorDataPoint</code>',
            'update-parameter-value': 'bar.EndTime, bar.Close'
        },
        'BarIndicator': {
            'name': 'bar-indicator',
            'update-parameter-type': 'a <code>TradeBar</code> or <code>QuoteBar</code>',
            'update-parameter-value': 'bar'
        },
        'TradeBarIndicator': {
            'name': 'trade-bar-indicator',
            'update-parameter-type': 'a <code>TradeBar</code>',
            'update-parameter-value': 'bar'
        }
    }

    # Get Indicator Type
    def find_indicator_type(base_type):
        if 'CandlestickPatterns' in base_type:
            return types["TradeBarIndicator"]

        for k, v in types.items():
            if f'QuantConnect.Indicators.{k}' in base_type:
                return v
        key = ' '.join(re.findall('[a-zA-Z][^A-Z]*', base_type.split('.')[-1]))
        base = indicators.get(key, get_type(base_type))
        return find_indicator_type(base['base-type-full-name'])

    for key, indicator in indicators.items():
        indicator_type = find_indicator_type(indicator['base-type-full-name'])
        indicator['update-parameter-type'] = indicator_type['update-parameter-type']
        indicator['update-parameter-value'] = indicator_type['update-parameter-value']

    # DELETE ALL FILES
    rmtree(INDICATORS, ignore_errors=True)
    Path(f'{INDICATORS}/00 Candlestick Patterns/').mkdir(parents=True, exist_ok=True)

    count = 0
    candle = 0
    for key in sorted(indicators.keys()):
        indicator = indicators.get(key)
        if 'CandlestickPatterns' in indicator['full-type-name']:
            candle += 1
            indicator['folder'] = Path(f'{INDICATORS}/00 Candlestick Patterns/{candle:02} {key}')
        else:
            count += 1
            indicator['folder'] = Path(f'{INDICATORS}/{count:03} {key}')

    with open('Resources/indicators/indicator_count.html', 'w', encoding='utf-8') as fp:
        fp.write(f'There are {count} indicators.')

    with open('Resources/indicators/candlestick_pattern_count.html', 'w', encoding='utf-8') as fp:
        fp.write(f'There are {candle} candlestick pattern indicators.')

    _generate_landing_page(0, count, INDICATORS, 'Supported Indicators',
        '<p>Indicators translate a stream of data points into a numerical value you can use to detect trading opportunities. LEAN provides more than 100 pre-built technical indicators and candlestick patterns you can use in your algorithms. You can use any of the following indicators. Click one to learn more.</p>')

    _generate_landing_page(1, 1+candle, f'{INDICATORS}/00 Candlestick Patterns', 'Candlestick Patterns',
        '<p>You can use any of the following candlestick patterns. Click one to learn more.</p>')

    for key, indicator in indicators.items():
        folder = indicator['folder']
        folder.mkdir(parents=True, exist_ok=True)

        type_name = indicator['type-name']
        description = indicator['description']
        helper_name = indicator['helper-name']
        image_source = _get_image_source(folder)
        source = indicator['source']

        with open(f'{folder}/01 Introduction.html', 'w', encoding='utf-8') as fp:
            category = 'candlestick pattern' if 'CandlestickPatterns' in source else 'indicator'
            fp.write(f"""{TAG}
<p>{description}</p>
<p>To view the implementation of this {category}, see the <a rel="nofollow" target="_blank" href="{source}">LEAN GitHub repository</a>.</p>""")

        with open(f'{folder}/02 Using {helper_name} Indicator.php', 'w', encoding='utf-8') as fp:
            fp.write(f"""{TAG}
<? 
include(DOCS_RESOURCES."/qcalgorithm-api/_method_container.html");

$hasReference = { 'true' if 'reference' in indicator['helper-arguments'] else 'false' };
$hasAutomaticIndicatorHelper = {'true' if type_name != 'Delay' else 'false'};
$helperPrefix = '{'CandlestickPatterns.' if 'CandlestickPatterns' in source else ''}';
$typeName = '{type_name}';
$helperName = '{helper_name}';
$helperArguments = '{indicator['helper-arguments']}';
$properties = {indicator['properties'][0]};
$otherProperties = {indicator['properties'][1]};
$updateParameterType = '{indicator['update-parameter-type']}';
$constructorArguments = '{indicator['constructor-arguments'] if indicator['constructor-arguments'] else ''}';
$updateParameterValue = '{indicator['update-parameter-value']}';
$hasMovingAverageTypeParameter = {indicator['has-moving-average-type-parameter']};
$constructorBox = '{key.lower().replace(' ','-')}';
$isOptionIndicator = { 'true' if type_name in OPTION_INDICATORS else 'false' };
include(DOCS_RESOURCES."/indicators/using-indicator.php");
?>""")

        if 'CandlestickPatterns' not in indicator['full-type-name']:
            with open(f'{folder}/03 Visualization.php', 'w', encoding='utf-8') as fp:
                fp.write(f"""{TAG}
<?
$typeName = "{type_name}";
$imageSource = "{image_source}";
include(DOCS_RESOURCES."/indicators/visualization.php");
?>""")
            image_source = _replace_last_occurrence(image_source, "/", "/-")

        if description.find('<see cref=\"T:') > 0:
            description = description.replace('<see cref=\"T:','').replace('\" />','')
        if len(description) > 127:
            description = description[:127] + '...'
        with open(f'{folder}/metadata.json', 'w', encoding='utf-8') as fp:
            metadata = {
                'type': 'metadata',
                'values': {
                    'description': description,
                    'keywords': key.lower(),
                    'og:type': 'website',
                    'og:description': description,
                    'og:title': f'{key} - Using Indicators on QuantConnect.com',
                    'og:site_name': f'{key} - Using Indicators on QuantConnect.com',
                    'og:image': image_source
                }
            }
            fp.write(dumps(metadata, indent=4))

if __name__ == '__main__':
    Generate_Indicators_Reference()