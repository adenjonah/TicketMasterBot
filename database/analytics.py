"""
Time series analytics functions for analyzing regional event data.
"""
from datetime import datetime, timezone, timedelta
from config.logging import logger

async def get_region_activity_by_hour(conn, region_id=None, days_ago=30):
    """
    Retrieve hourly activity for a specific region or all regions.
    
    Args:
        conn: Database connection
        region_id: Specific region to analyze or None for all regions
        days_ago: Number of days to look back
        
    Returns:
        List of dictionaries with hourly activity data
    """
    start_date = datetime.now(timezone.utc) - timedelta(days=days_ago)
    
    query = """
    SELECT 
        ServerID, 
        hour_of_day,
        AVG(events_returned) as avg_events,
        AVG(new_events) as avg_new_events,
        COUNT(*) as sample_count
    FROM 
        ServerTimeSeries
    WHERE 
        timestamp > $1
    """
    
    params = [start_date]
    
    # Add region filter if specified
    if region_id:
        query += " AND ServerID = $2"
        params.append(region_id)
        
    query += """
    GROUP BY 
        ServerID, hour_of_day
    ORDER BY 
        ServerID, hour_of_day
    """
    
    try:
        results = await conn.fetch(query, *params)
        return [dict(row) for row in results]
    except Exception as e:
        logger.error(f"Error retrieving hourly activity data: {e}", exc_info=True)
        return []

async def get_region_activity_by_day(conn, region_id=None, days_ago=30):
    """
    Retrieve daily activity for a specific region or all regions.
    
    Args:
        conn: Database connection
        region_id: Specific region to analyze or None for all regions
        days_ago: Number of days to look back
        
    Returns:
        List of dictionaries with daily activity data
    """
    start_date = datetime.now(timezone.utc) - timedelta(days=days_ago)
    
    query = """
    SELECT 
        ServerID, 
        day_of_week,
        AVG(events_returned) as avg_events,
        AVG(new_events) as avg_new_events,
        COUNT(*) as sample_count
    FROM 
        ServerTimeSeries
    WHERE 
        timestamp > $1
    """
    
    params = [start_date]
    
    # Add region filter if specified
    if region_id:
        query += " AND ServerID = $2"
        params.append(region_id)
        
    query += """
    GROUP BY 
        ServerID, day_of_week
    ORDER BY 
        ServerID, day_of_week
    """
    
    try:
        results = await conn.fetch(query, *params)
        return [dict(row) for row in results]
    except Exception as e:
        logger.error(f"Error retrieving daily activity data: {e}", exc_info=True)
        return []

async def get_region_trending_data(conn, region_id=None, days_ago=7, interval_hours=6):
    """
    Get trending data to compare recent activity with previous periods.
    
    Args:
        conn: Database connection
        region_id: Specific region to analyze or None for all regions
        days_ago: Number of days to look back
        interval_hours: Interval size in hours for aggregation
        
    Returns:
        Dictionary with trending data comparing recent vs past periods
    """
    now = datetime.now(timezone.utc)
    recent_start = now - timedelta(days=days_ago//2)
    past_start = now - timedelta(days=days_ago)
    
    # Base query for both periods
    base_query = """
    SELECT 
        ServerID,
        SUM(events_returned) as total_events,
        SUM(new_events) as total_new_events,
        COUNT(*) as data_points
    FROM 
        ServerTimeSeries
    WHERE 
        timestamp >= $1 AND timestamp < $2
    """
    
    # Add region filter if specified
    if region_id:
        base_query += " AND ServerID = $3"
        group_by = "GROUP BY ServerID"
    else:
        group_by = "GROUP BY ServerID"
    
    # Complete the queries
    recent_query = base_query + f" {group_by}"
    past_query = base_query + f" {group_by}"
    
    try:
        # Get recent period data
        if region_id:
            recent_results = await conn.fetch(recent_query, recent_start, now, region_id)
            past_results = await conn.fetch(past_query, past_start, recent_start, region_id)
        else:
            recent_results = await conn.fetch(recent_query, recent_start, now)
            past_results = await conn.fetch(past_query, past_start, recent_start)
        
        # Process results into comparable format
        recent_data = {row['serverid']: dict(row) for row in recent_results}
        past_data = {row['serverid']: dict(row) for row in past_results}
        
        # Calculate trends
        trends = {}
        for server_id in set(list(recent_data.keys()) + list(past_data.keys())):
            recent = recent_data.get(server_id, {'total_events': 0, 'total_new_events': 0, 'data_points': 0})
            past = past_data.get(server_id, {'total_events': 0, 'total_new_events': 0, 'data_points': 0})
            
            # Normalize by data points to get average per interval
            recent_avg_events = recent['total_events'] / max(1, recent['data_points'])
            recent_avg_new = recent['total_new_events'] / max(1, recent['data_points'])
            
            past_avg_events = past['total_events'] / max(1, past['data_points'])
            past_avg_new = past['total_new_events'] / max(1, past['data_points'])
            
            # Calculate percent change
            events_change = ((recent_avg_events - past_avg_events) / max(1, past_avg_events)) * 100 if past_avg_events > 0 else 0
            new_events_change = ((recent_avg_new - past_avg_new) / max(1, past_avg_new)) * 100 if past_avg_new > 0 else 0
            
            trends[server_id] = {
                'recent_avg_events': recent_avg_events,
                'recent_avg_new_events': recent_avg_new,
                'past_avg_events': past_avg_events,
                'past_avg_new_events': past_avg_new,
                'events_percent_change': events_change,
                'new_events_percent_change': new_events_change,
                'is_trending_up': events_change > 0 or new_events_change > 0
            }
        
        return trends
    except Exception as e:
        logger.error(f"Error retrieving trending data: {e}", exc_info=True)
        return {}

async def get_hourly_heatmap_data(conn, days_ago=30):
    """
    Get data for a heatmap visualization showing activity by hour and region.
    
    Args:
        conn: Database connection
        days_ago: Number of days to look back
        
    Returns:
        List of dictionaries with hour, region, and event counts
    """
    start_date = datetime.now(timezone.utc) - timedelta(days=days_ago)
    
    query = """
    SELECT 
        ServerID,
        hour_of_day,
        AVG(new_events) as avg_new_events
    FROM 
        ServerTimeSeries
    WHERE 
        timestamp > $1
    GROUP BY 
        ServerID, hour_of_day
    ORDER BY 
        ServerID, hour_of_day
    """
    
    try:
        results = await conn.fetch(query, start_date)
        return [dict(row) for row in results]
    except Exception as e:
        logger.error(f"Error retrieving heatmap data: {e}", exc_info=True)
        return [] 