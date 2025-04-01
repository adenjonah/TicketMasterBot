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
        SUM(new_events) as total_new_events,
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
        SUM(new_events) as total_new_events,
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
        SUM(new_events) as total_new_events
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

async def get_notable_events_by_hour(conn, region_id=None, days_ago=30):
    """
    Retrieve hourly activity for notable artist events.
    
    Args:
        conn: Database connection
        region_id: Specific region to analyze or None for all regions
        days_ago: Number of days to look back
        
    Returns:
        List of dictionaries with hourly notable event activity data
    """
    start_date = datetime.now(timezone.utc) - timedelta(days=days_ago)
    
    query = """
    SELECT 
        region, 
        hour_of_day,
        AVG(total_events) as avg_events,
        SUM(new_events) as total_new_events,
        COUNT(*) as sample_count
    FROM 
        NotableEventsTimeSeries
    WHERE 
        timestamp > $1
    """
    
    params = [start_date]
    
    # Add region filter if specified
    if region_id:
        query += " AND region = $2"
        params.append(region_id)
        
    query += """
    GROUP BY 
        region, hour_of_day
    ORDER BY 
        region, hour_of_day
    """
    
    try:
        results = await conn.fetch(query, *params)
        return [dict(row) for row in results]
    except Exception as e:
        logger.error(f"Error retrieving notable events hourly data: {e}", exc_info=True)
        return []

async def get_notable_events_by_day(conn, region_id=None, days_ago=30):
    """
    Retrieve daily activity for notable artist events.
    
    Args:
        conn: Database connection
        region_id: Specific region to analyze or None for all regions
        days_ago: Number of days to look back
        
    Returns:
        List of dictionaries with daily notable event activity data
    """
    start_date = datetime.now(timezone.utc) - timedelta(days=days_ago)
    
    query = """
    SELECT 
        region, 
        day_of_week,
        AVG(total_events) as avg_events,
        SUM(new_events) as total_new_events,
        COUNT(*) as sample_count
    FROM 
        NotableEventsTimeSeries
    WHERE 
        timestamp > $1
    """
    
    params = [start_date]
    
    # Add region filter if specified
    if region_id:
        query += " AND region = $2"
        params.append(region_id)
        
    query += """
    GROUP BY 
        region, day_of_week
    ORDER BY 
        region, day_of_week
    """
    
    try:
        results = await conn.fetch(query, *params)
        return [dict(row) for row in results]
    except Exception as e:
        logger.error(f"Error retrieving notable events daily data: {e}", exc_info=True)
        return []

async def compare_notable_vs_all_events(conn, region_id=None, days_ago=30):
    """
    Compare the proportion of notable events vs. all events.
    
    Args:
        conn: Database connection
        region_id: Specific region to analyze or None for all regions
        days_ago: Number of days to look back
        
    Returns:
        Dictionary with comparison data between notable and all events
    """
    start_date = datetime.now(timezone.utc) - timedelta(days=days_ago)
    
    # Query for all events
    all_events_query = """
    SELECT 
        ServerID as region,
        SUM(new_events) as total_new_events,
        COUNT(*) as data_points
    FROM 
        ServerTimeSeries
    WHERE 
        timestamp > $1
    """
    
    # Query for notable events
    notable_events_query = """
    SELECT 
        region,
        SUM(new_events) as total_new_events,
        COUNT(*) as data_points
    FROM 
        NotableEventsTimeSeries
    WHERE 
        timestamp > $1
    """
    
    params = [start_date]
    
    # Add region filter if specified
    if region_id:
        all_events_query += " AND ServerID = $2"
        notable_events_query += " AND region = $2"
        params.append(region_id)
    
    # Group by region
    all_events_query += " GROUP BY ServerID"
    notable_events_query += " GROUP BY region"
    
    try:
        # Get data for all events
        all_events_results = await conn.fetch(all_events_query, *params)
        all_events_data = {row['region']: dict(row) for row in all_events_results}
        
        # Get data for notable events
        notable_events_results = await conn.fetch(notable_events_query, *params)
        notable_events_data = {row['region']: dict(row) for row in notable_events_results}
        
        # Calculate comparisons
        comparisons = {}
        for region in set(list(all_events_data.keys()) + list(notable_events_data.keys())):
            all_events = all_events_data.get(region, {'total_new_events': 0, 'data_points': 0})
            notable_events = notable_events_data.get(region, {'total_new_events': 0, 'data_points': 0})
            
            # Calculate percentages
            total_new_all = all_events['total_new_events']
            total_new_notable = notable_events['total_new_events']
            
            # Avoid division by zero
            percentage = (total_new_notable / total_new_all * 100) if total_new_all > 0 else 0
            
            comparisons[region] = {
                'total_events': total_new_all,
                'notable_events': total_new_notable,
                'percentage_notable': percentage
            }
        
        return comparisons
    except Exception as e:
        logger.error(f"Error comparing notable vs all events: {e}", exc_info=True)
        return {} 