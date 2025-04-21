-- Fix European Events SQL Script
-- Run with: heroku pg:psql < fix_eu_events.sql

-- Show current region distribution
SELECT region, COUNT(*) 
FROM Events 
GROUP BY region
ORDER BY COUNT(*) DESC;

-- Check for European events
SELECT COUNT(*) 
FROM Events 
WHERE LOWER(region) = 'eu';

-- Fix capitalization issues
UPDATE Events
SET region = 'eu'
WHERE region IN ('EU', 'Eu', 'eU', 'europe', 'Europe', 'EUROPE');

-- Mark all European events as unsent
UPDATE Events
SET sentToDiscord = FALSE
WHERE LOWER(region) = 'eu';

-- Check unsent European events
SELECT COUNT(*) AS unsent_eu_count
FROM Events 
WHERE sentToDiscord = FALSE AND LOWER(region) = 'eu';

-- Show sample of unsent European events
SELECT eventID, name, region, sentToDiscord
FROM Events
WHERE LOWER(region) = 'eu' AND sentToDiscord = FALSE
LIMIT 5; 