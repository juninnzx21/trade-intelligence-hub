param(
    [string]$BaseUrl = "https://roboiqopition.juninnzxtec.com.br",
    [string]$Token = ""
)

$headers = @{}
if ($Token -ne "") {
    $headers["Authorization"] = "Bearer $Token"
}

Write-Host "GET $BaseUrl/api/v1/health/detailed"
Invoke-RestMethod -Uri "$BaseUrl/api/v1/health/detailed" -Headers $headers -Method Get | ConvertTo-Json -Depth 6

Write-Host "GET $BaseUrl/api/v1/market/status"
Invoke-RestMethod -Uri "$BaseUrl/api/v1/market/status" -Headers $headers -Method Get | ConvertTo-Json -Depth 6

Write-Host "GET $BaseUrl/api/v1/market/latest?asset=EUR/USD&timeframe=15m"
Invoke-RestMethod -Uri "$BaseUrl/api/v1/market/latest?asset=EUR/USD&timeframe=15m" -Headers $headers -Method Get | ConvertTo-Json -Depth 6

$body = @{
    asset = "EUR/USD"
    timeframe = "M1"
} | ConvertTo-Json -Compress

Write-Host "POST $BaseUrl/api/v1/market/analyze"
Invoke-RestMethod -Uri "$BaseUrl/api/v1/market/analyze" -Headers $headers -Method Post -ContentType "application/json" -Body $body | ConvertTo-Json -Depth 6
