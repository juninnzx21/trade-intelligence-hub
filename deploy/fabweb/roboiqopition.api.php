<?php
declare(strict_types=1);

date_default_timezone_set('America/Sao_Paulo');

function iso_offset(int $minutes): string
{
    $dt = new DateTimeImmutable('now', new DateTimeZone('America/Sao_Paulo'));
    return $dt->modify(($minutes >= 0 ? '+' : '') . $minutes . ' minutes')->format(DATE_ATOM);
}

function dashboard_payload(): array
{
    return [
        'summary' => [
            'total_signals' => 3,
            'buy_signals' => 1,
            'sell_signals' => 2,
            'no_trade_signals' => 0,
            'win_rate' => 0,
            'best_symbol' => 'EUR/USD',
            'best_timeframe' => '15m',
            'active_alerts' => 2,
            'premium_opportunities' => 0,
        ],
        'opportunities' => [
            [
                'symbol' => 'EUR/USD',
                'market' => 'FOREX',
                'timeframe' => '15m',
                'score' => 76.4,
                'decision' => 'COMPRA',
                'risk_level' => 'Moderado',
                'trend' => 'alta',
                'reasons' => ['Tendencia primaria de alta confirmada', 'Spread favoravel para execucao', 'Historico semelhante positivo'],
            ],
            [
                'symbol' => 'GBP/USD',
                'market' => 'FOREX',
                'timeframe' => '1h',
                'score' => 72.35,
                'decision' => 'VENDA',
                'risk_level' => 'Moderado',
                'trend' => 'baixa',
                'reasons' => ['Tendencia primaria de baixa confirmada', 'Pressao vendedora consistente', 'Historico semelhante positivo'],
            ],
        ],
        'live_board' => [
            [
                'symbol' => 'EUR/USD',
                'market' => 'FOREX',
                'timeframe' => '15m',
                'provider' => 'Fabweb Observer Feed',
                'score' => 76.4,
                'decision' => 'COMPRA',
                'risk_level' => 'Moderado',
                'entry_time' => iso_offset(2),
                'exit_time' => iso_offset(17),
                'duration' => '15 minutos',
                'signal_valid_until' => iso_offset(3),
                'trend' => 'alta',
                'spread' => 0.7,
                'volatility' => 1.2,
                'technical_reasons' => ['Tendencia primaria de alta confirmada', 'Preco acima da media movel'],
                'fundamental_reasons' => ['Sem noticia forte imediata'],
                'block_reasons' => [],
                'reasons' => ['Tendencia primaria de alta confirmada', 'Spread favoravel para execucao', 'Historico semelhante positivo'],
                'indicator_snapshot' => ['rsi' => 61.4, 'macd' => 0.18, 'atr' => 0.0009, 'vwap' => 1.084, 'trend_primary' => 'alta', 'volatility_pct' => 1.2, 'spread' => 0.7],
            ],
            [
                'symbol' => 'GBP/USD',
                'market' => 'FOREX',
                'timeframe' => '1h',
                'provider' => 'Fabweb Observer Feed',
                'score' => 72.35,
                'decision' => 'VENDA',
                'risk_level' => 'Moderado',
                'entry_time' => iso_offset(5),
                'exit_time' => iso_offset(65),
                'duration' => '1 hora',
                'signal_valid_until' => iso_offset(7),
                'trend' => 'baixa',
                'spread' => 1.0,
                'volatility' => 2.0,
                'technical_reasons' => ['Tendencia primaria de baixa confirmada', 'Momentum vendedor sustentado'],
                'fundamental_reasons' => ['Contexto macro pressionando a libra'],
                'block_reasons' => [],
                'reasons' => ['Tendencia primaria de baixa confirmada', 'Pressao vendedora consistente', 'Historico semelhante positivo'],
                'indicator_snapshot' => ['rsi' => 41.2, 'macd' => -0.22, 'atr' => 0.0018, 'vwap' => 1.2662, 'trend_primary' => 'baixa', 'volatility_pct' => 2.0, 'spread' => 1.0],
            ],
            [
                'symbol' => 'ETH/USDT',
                'market' => 'CRYPTO',
                'timeframe' => '5m',
                'provider' => 'Fabweb Observer Feed',
                'score' => 68.1,
                'decision' => 'VENDA',
                'risk_level' => 'Moderado',
                'entry_time' => iso_offset(1),
                'exit_time' => iso_offset(6),
                'duration' => '5 minutos',
                'signal_valid_until' => iso_offset(2),
                'trend' => 'baixa',
                'spread' => 1.5,
                'volatility' => 2.4,
                'technical_reasons' => ['Pullback falhou na resistencia', 'Volatilidade ainda controlada'],
                'fundamental_reasons' => ['Sem evento macro imediato de alto impacto'],
                'block_reasons' => [],
                'reasons' => ['Pullback falhou na resistencia', 'Volatilidade ainda controlada', 'Contexto observador sem execucao real'],
                'indicator_snapshot' => ['rsi' => 44.8, 'macd' => -1.9, 'atr' => 18.4, 'vwap' => 3188.5, 'trend_primary' => 'baixa', 'volatility_pct' => 2.4, 'spread' => 1.5],
            ],
        ],
        'signals' => [
            [
                'id' => 1,
                'timestamp' => iso_offset(-15),
                'symbol' => 'EUR/USD',
                'market' => 'FOREX',
                'timeframe' => '15m',
                'decision' => 'COMPRA',
                'score' => 76.4,
                'risk_level' => 'Moderado',
                'entry_time' => iso_offset(2),
                'exit_time' => iso_offset(17),
                'duration' => '15 minutos',
                'signal_valid_until' => iso_offset(3),
                'trend' => 'alta',
                'reasoning' => 'Tendencia primaria de alta confirmada | Spread favoravel para execucao | Historico semelhante positivo',
            ],
            [
                'id' => 2,
                'timestamp' => iso_offset(-10),
                'symbol' => 'GBP/USD',
                'market' => 'FOREX',
                'timeframe' => '1h',
                'decision' => 'VENDA',
                'score' => 72.35,
                'risk_level' => 'Moderado',
                'entry_time' => iso_offset(5),
                'exit_time' => iso_offset(65),
                'duration' => '1 hora',
                'signal_valid_until' => iso_offset(7),
                'trend' => 'baixa',
                'reasoning' => 'Tendencia primaria de baixa confirmada | Pressao vendedora consistente | Historico semelhante positivo',
            ],
            [
                'id' => 3,
                'timestamp' => iso_offset(-5),
                'symbol' => 'ETH/USDT',
                'market' => 'CRYPTO',
                'timeframe' => '5m',
                'decision' => 'VENDA',
                'score' => 68.1,
                'risk_level' => 'Moderado',
                'entry_time' => iso_offset(1),
                'exit_time' => iso_offset(6),
                'duration' => '5 minutos',
                'signal_valid_until' => iso_offset(2),
                'trend' => 'baixa',
                'reasoning' => 'Pullback falhou na resistencia | Volatilidade ainda controlada | Contexto observador sem execucao real',
            ],
        ],
        'economic_events' => [
            [
                'event_time' => iso_offset(60),
                'region' => 'US',
                'title' => 'Payroll',
                'impact' => 'ALTO',
                'source' => 'Calendario Economico Publico',
                'summary' => 'Divulgacao com potencial de ampliar a volatilidade em pares dolarizados.',
            ],
            [
                'event_time' => iso_offset(240),
                'region' => 'EU',
                'title' => 'Fala de dirigente do BCE',
                'impact' => 'MEDIO',
                'source' => 'Noticias Financeiras Publicas',
                'summary' => 'Monitoramento de comunicacao oficial para impacto em EUR crosses.',
            ],
        ],
        'integrations' => [
            ['name' => 'Binance', 'category' => 'Mercado', 'status' => 'ativo', 'auth_type' => 'publica', 'base_url' => 'https://api.binance.com', 'notes' => 'Klines e spread publico para cripto.'],
            ['name' => 'OANDA', 'category' => 'Mercado', 'status' => 'aguardando-chave', 'auth_type' => 'api-key', 'base_url' => 'https://api-fxpractice.oanda.com', 'notes' => 'Conta demo oficial pronta para integracao.'],
            ['name' => 'Calendario Economico Publico', 'category' => 'Macro', 'status' => 'observador', 'auth_type' => 'publica', 'base_url' => 'https://www.forexfactory.com/calendar', 'notes' => 'Somente fontes publicas permitidas.'],
        ],
        'modules' => [
            ['name' => 'Data Collector', 'mode' => 'observer', 'enabled' => true, 'description' => 'Coleta snapshots, contexto e eventos.'],
            ['name' => 'Technical Engine', 'mode' => 'active', 'enabled' => true, 'description' => 'Calcula indicadores, estrutura e momentum.'],
            ['name' => 'Macro Engine', 'mode' => 'observer', 'enabled' => true, 'description' => 'Agenda economica e manchetes publicas.'],
            ['name' => 'Forward Test', 'mode' => 'observer', 'enabled' => true, 'description' => 'Registra sinais ao vivo sem executar ordens.'],
        ],
        'monitored_assets' => [
            ['symbol' => 'EUR/USD', 'market' => 'FOREX', 'provider' => 'OANDA-ready', 'priority' => 1, 'enabled' => true, 'timeframes' => ['1m', '5m', '15m', '1h']],
            ['symbol' => 'GBP/USD', 'market' => 'FOREX', 'provider' => 'OANDA-ready', 'priority' => 1, 'enabled' => true, 'timeframes' => ['5m', '15m', '1h']],
            ['symbol' => 'BTC/USDT', 'market' => 'CRYPTO', 'provider' => 'Binance', 'priority' => 1, 'enabled' => true, 'timeframes' => ['1m', '5m', '15m', '1h']],
            ['symbol' => 'ETH/USDT', 'market' => 'CRYPTO', 'provider' => 'Binance', 'priority' => 2, 'enabled' => true, 'timeframes' => ['5m', '15m', '1h']],
        ],
        'risk_profile' => [
            'profile_name' => 'default-observer',
            'stake_percent' => 0.8,
            'daily_stop_percent' => 2.5,
            'daily_target_percent' => 1.8,
            'max_consecutive_losses' => 3,
            'cooldown_minutes' => 45,
            'observer_mode' => true,
        ],
        'backtests' => [
            ['strategy_name' => 'Trend + Pullback + Macro Filter', 'symbol' => 'EUR/USD', 'timeframe' => '15m', 'win_rate' => 62.4, 'payoff' => 1.48, 'drawdown' => 7.2, 'net_profit' => 18.6, 'worst_streak' => 4, 'best_hour' => '10:00 UTC', 'risk_label' => 'Moderado'],
            ['strategy_name' => 'Breakout + VWAP + Sentiment', 'symbol' => 'BTC/USDT', 'timeframe' => '5m', 'win_rate' => 58.3, 'payoff' => 1.61, 'drawdown' => 10.8, 'net_profit' => 26.2, 'worst_streak' => 5, 'best_hour' => '13:00 UTC', 'risk_label' => 'Moderado'],
        ],
        'forward_tests' => [
            ['window_name' => '30d observer', 'signals_count' => 512, 'win_rate' => 57.9, 'average_score' => 68.4, 'status' => 'validando', 'notes' => 'Base minima de 500 sinais atingida em ambiente sem dinheiro.'],
            ['window_name' => '7d quality pulse', 'signals_count' => 119, 'win_rate' => 60.5, 'average_score' => 71.2, 'status' => 'em_coleta', 'notes' => 'Concentrando apenas leituras acima de 66 pontos.'],
        ],
        'audits' => [
            ['created_at' => iso_offset(-42), 'actor' => 'system', 'action' => 'fabweb:fallback', 'details' => 'Fallback observador ativo na Fabweb enquanto a VPS esta indisponivel.'],
            ['created_at' => iso_offset(-19), 'actor' => 'system', 'action' => 'backtest:refresh', 'details' => 'Metricas recalculadas por estrategia.'],
        ],
        'users' => [
            ['name' => 'Admin Operator', 'email' => 'admin@tradehub.local', 'role' => 'admin', 'status' => 'active', 'two_factor_enabled' => true],
            ['name' => 'Risk Analyst', 'email' => 'risk@tradehub.local', 'role' => 'analyst', 'status' => 'active', 'two_factor_enabled' => true],
            ['name' => 'Observer Seat', 'email' => 'observer@tradehub.local', 'role' => 'viewer', 'status' => 'pilot', 'two_factor_enabled' => false],
        ],
        'alert_channels' => [
            ['name' => 'Telegram Ops', 'channel_type' => 'telegram', 'status' => 'planned', 'destination' => '@trade_ops', 'notes' => 'Pronto para fase de alertas.'],
            ['name' => 'WhatsApp Desk', 'channel_type' => 'whatsapp', 'status' => 'planned', 'destination' => '+55-00-0000-0000', 'notes' => 'Somente notificacao, nunca promessa de ganho.'],
            ['name' => 'Mobile Push', 'channel_type' => 'push', 'status' => 'observer', 'destination' => 'ios/android', 'notes' => 'Usado para sinais fortes e bloqueios macro.'],
        ],
        'security_controls' => [
            ['name' => 'API keys encryption', 'status' => 'designed', 'severity' => 'high', 'details' => 'Chaves preparadas para criptografia em repouso.'],
            ['name' => 'Audit logging', 'status' => 'active', 'severity' => 'high', 'details' => 'Acoes do motor e do admin sao registradas.'],
            ['name' => '2FA optional', 'status' => 'planned', 'severity' => 'medium', 'details' => 'Usuarios premium podem exigir segundo fator.'],
            ['name' => 'Backup policy', 'status' => 'planned', 'severity' => 'medium', 'details' => 'Backups diarios seguem no roadmap operacional.'],
        ],
        'scraping_sources' => [
            ['name' => 'Economic Calendar', 'scope' => 'macro', 'status' => 'observer', 'policy' => 'Somente pagina publica, sem login, captcha ou bypass.'],
            ['name' => 'Financial Headlines', 'scope' => 'news', 'status' => 'observer', 'policy' => 'Manchetes publicas e metadata de impacto apenas.'],
            ['name' => 'Central Bank Statements', 'scope' => 'macro', 'status' => 'planned', 'policy' => 'Captura de comunicados publicos oficiais.'],
        ],
    ];
}

$path = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH) ?: '/';
$payload = dashboard_payload();

if ($path === '/api/v1/health/detailed') {
    header('Content-Type: application/json; charset=UTF-8');
    echo json_encode([
        'status' => 'ok',
        'database' => 'fabweb-fallback',
        'redis_channel' => 'disabled',
        'signals' => count($payload['signals']),
        'live_board_cached' => count($payload['live_board']),
    ], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

if ($path === '/api/v1/dashboard' || $path === '/api/v1/reports/export') {
    header('Content-Type: application/json; charset=UTF-8');
    echo json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

if ($path === '/api/v1/market/live-board' || $path === '/api/v1/market/live-board/refresh') {
    header('Content-Type: application/json; charset=UTF-8');
    echo json_encode($payload['live_board'], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

if ($path === '/api/v1/reports/export.csv') {
    header('Content-Type: text/csv; charset=UTF-8');
    header('Content-Disposition: attachment; filename="trade-intelligence-hub-fallback.csv"');
    echo "timestamp,symbol,market,timeframe,decision,score,risk_level\n";
    foreach ($payload['signals'] as $signal) {
        echo implode(',', [
            $signal['timestamp'],
            $signal['symbol'],
            $signal['market'],
            $signal['timeframe'],
            $signal['decision'],
            (string) $signal['score'],
            $signal['risk_level'],
        ]) . "\n";
    }
    exit;
}

http_response_code(404);
header('Content-Type: application/json; charset=UTF-8');
echo json_encode(['detail' => 'Not found'], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
