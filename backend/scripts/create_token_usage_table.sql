-- Create Athena table for token usage data
-- Run this in Athena console to create the table for querying token usage logs

CREATE EXTERNAL TABLE IF NOT EXISTS token_usage (
  timestamp string,
  user_id string,
  chat_id string,
  input_tokens int,
  output_tokens int,
  total_tokens int,
  model_id string
)
PARTITIONED BY (
  year int,
  month int,
  day int
)
STORED AS TEXTFILE
LOCATION 's3://sera-token-usage-data-<ACCOUNT_ID>/'
TBLPROPERTIES (
  'projection.enabled'='true',
  'projection.year.type'='integer',
  'projection.year.range'='2024,2030',
  'projection.month.type'='integer',
  'projection.month.range'='1,12',
  'projection.day.type'='integer',
  'projection.day.range'='1,31',
  'storage.location.template'='s3://sera-token-usage-data-<ACCOUNT_ID>/year=${year}/month=${month}/day=${day}/'
);

-- Example queries:

-- Daily token usage by user
-- SELECT 
--   user_id,
--   year, month, day,
--   SUM(total_tokens) as daily_tokens,
--   COUNT(*) as api_calls
-- FROM token_usage 
-- WHERE year = 2024 AND month = 9 AND day = 25
-- GROUP BY user_id, year, month, day
-- ORDER BY daily_tokens DESC;

-- Hourly API call rate (for quota analysis)
-- SELECT 
--   SUBSTR(timestamp, 1, 13) as hour,
--   COUNT(*) as calls_per_hour,
--   SUM(total_tokens) as tokens_per_hour
-- FROM token_usage 
-- WHERE year = 2024 AND month = 9 AND day = 25
-- GROUP BY SUBSTR(timestamp, 1, 13)
-- ORDER BY hour;

-- Top users by token consumption
-- SELECT 
--   user_id,
--   SUM(total_tokens) as total_tokens,
--   COUNT(*) as total_calls,
--   AVG(total_tokens) as avg_tokens_per_call
-- FROM token_usage 
-- WHERE year = 2024 AND month = 9
-- GROUP BY user_id
-- ORDER BY total_tokens DESC
-- LIMIT 10;
