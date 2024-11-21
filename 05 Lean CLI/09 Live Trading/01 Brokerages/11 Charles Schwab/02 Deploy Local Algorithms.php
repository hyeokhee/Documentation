<?
$brokerageName = "Charles Schwab";
$dataFeedName = "";
$isBrokerage = true;
$brokerageDetails = "
<li>Enter your Charles Schwab credentials.
<div class='cli section-example-container'>
<pre>$ lean live \"My Project\"
API key:
OAuth Access Token: 
Account number: </pre>
</div>
<p>To get your account credentials, see <a href='https://www.quantconnect.com/docs/v2/cloud-platform/live-trading/brokerages/charles-schwab#02-Account-Types'>Account Types</a>.</p>
</li>
";
$dataFeedDetails = "";
$supportsIQFeed = true;
$requiresSubscription = true;
include(DOCS_RESOURCES."/brokerages/cli-deployment/deploy-local-algorithms.php");
?>
