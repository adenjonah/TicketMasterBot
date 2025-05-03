import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import io
import numpy as np
import discord
from datetime import datetime, timezone
from matplotlib.colors import LinearSegmentedColormap

DISCORD_BLUE = "#5865F2"
DISCORD_GREEN = "#57F287"
DISCORD_YELLOW = "#FEE75C"
DISCORD_FUCHSIA = "#EB459E"
DISCORD_RED = "#ED4245"
DISCORD_PURPLE = "#9B59B6"

def create_discord_file(fig, filename):
    """Create a Discord file from a matplotlib figure."""
    buf = io.BytesIO()
    plt.tight_layout()
    fig.savefig(buf, format='png', dpi=100)
    buf.seek(0)
    return discord.File(buf, filename=filename)

def create_hour_plot(data, title, days, region=None):
    """Create an improved hourly plot with better styling."""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    regions = set(item.get('serverid', item.get('region')) for item in data)
    colors = [DISCORD_BLUE, DISCORD_GREEN, DISCORD_YELLOW, DISCORD_FUCHSIA, DISCORD_RED]
    
    for i, r in enumerate(regions):
        region_data = [item for item in data if item.get('serverid', item.get('region')) == r]
        hours = [item['hour_of_day'] for item in region_data]
        new_events = [item['total_new_events'] for item in region_data]
        
        # Add a smooth curve for better visualization
        ax.plot(hours, new_events, 'o-', label=r, linewidth=2, 
                color=colors[i % len(colors)], alpha=0.8)
    
    # Add average line if multiple regions
    if len(regions) > 1:
        all_hours = range(24)
        avg_events = []
        
        for hour in all_hours:
            hour_data = [item['total_new_events'] for item in data if item['hour_of_day'] == hour]
            if hour_data:
                avg_events.append(sum(hour_data) / len(hour_data))
            else:
                avg_events.append(0)
        
        ax.plot(all_hours, avg_events, '--', label='Average', 
                linewidth=2, color='gray', alpha=0.7)
    
    # Highlight peak hours
    hour_totals = {}
    for item in data:
        hour = item['hour_of_day']
        if hour not in hour_totals:
            hour_totals[hour] = 0
        hour_totals[hour] += item['total_new_events']
    
    if hour_totals:
        peak_hour = max(hour_totals, key=hour_totals.get)
        ax.axvspan(peak_hour - 0.5, peak_hour + 0.5, alpha=0.2, color='green')
        
        # Add annotation for peak hour
        ax.annotate(f'Peak Hour: {peak_hour}:00 UTC', 
                   xy=(peak_hour, hour_totals[peak_hour] * 0.9),
                   xytext=(peak_hour, hour_totals[peak_hour] * 1.1),
                   ha='center', fontsize=10,
                   bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.8))
    
    # Format the plot
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_xlabel("Hour of Day (UTC)", fontsize=12)
    ax.set_ylabel("Total New Events", fontsize=12)
    ax.set_xticks(range(0, 24))
    ax.set_xlim(-0.5, 23.5)
    
    # Add grid but make it subtle
    ax.grid(True, linestyle='--', alpha=0.3)
    
    # Add time zone indicators for reference
    time_zones = [
        {"name": "EST (US)", "offset": -5, "color": "blue"},
        {"name": "PST (US)", "offset": -8, "color": "green"},
        {"name": "GMT (UK)", "offset": 0, "color": "red"},
        {"name": "CET (EU)", "offset": 1, "color": "purple"}
    ]
    
    for tz in time_zones:
        # Convert from UTC to local midnight
        local_midnight_in_utc = (0 - tz["offset"]) % 24
        ax.axvline(x=local_midnight_in_utc, color=tz["color"], linestyle=':', alpha=0.5)
        ax.text(local_midnight_in_utc, ax.get_ylim()[1] * 0.95, 
                f"{tz['name']} Midnight", rotation=90, 
                verticalalignment='top', color=tz["color"], fontsize=8)
    
    # Customize legend
    ax.legend(title="Region", loc='upper right', fontsize=10, 
              title_fontsize=12, framealpha=0.7)
    
    # Add footer with info
    plt.figtext(0.5, 0.01, f"Data for past {days} days" + 
                (f" in {region}" if region else ""), 
                ha="center", fontsize=10, style='italic')
    
    return fig

def create_day_plot(data, title, days, day_names, region=None):
    """Create an improved daily plot with better styling."""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    regions = set(item.get('serverid', item.get('region')) for item in data)
    colors = [DISCORD_BLUE, DISCORD_GREEN, DISCORD_YELLOW, DISCORD_FUCHSIA, DISCORD_RED]
    
    # Create x positions for bars
    num_regions = len(regions)
    bar_width = 0.8 / num_regions if num_regions > 0 else 0.8
    offsets = np.linspace(-0.4 + bar_width/2, 0.4 - bar_width/2, num_regions)
    
    # Group and plot data by day and region
    for i, r in enumerate(regions):
        region_data = [item for item in data if item.get('serverid', item.get('region')) == r]
        # Sort by day of week (0 = Monday, 6 = Sunday)
        region_data.sort(key=lambda x: x['day_of_week'])
        
        # Create day mapping
        day_data = {d: 0 for d in range(7)}
        for item in region_data:
            day_data[item['day_of_week']] = item['total_new_events']
        
        days_of_week = list(day_data.keys())
        new_events = list(day_data.values())
        
        # Calculate positions for this region's bars
        x_pos = np.arange(len(days_of_week)) + offsets[i]
        
        # Use bar chart instead of line for clearer day comparison
        ax.bar(x_pos, new_events, width=bar_width, label=r, 
               color=colors[i % len(colors)], alpha=0.7)
    
    # Format the plot
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_xlabel("Day of Week", fontsize=12)
    ax.set_ylabel("Total New Events", fontsize=12)
    ax.set_xticks(range(0, 7))
    ax.set_xticklabels([day_names[d] for d in range(7)])
    
    # Add weekend highlight
    ax.axvspan(4.5, 6.5, alpha=0.1, color='yellow', label='Weekend')
    
    # Find highest day
    all_values = [item['total_new_events'] for item in data]
    if all_values:
        max_value = max(all_values)
        day_sums = {}
        for item in data:
            day = item['day_of_week']
            if day not in day_sums:
                day_sums[day] = 0
            day_sums[day] += item['total_new_events']
        
        if day_sums:
            busiest_day = max(day_sums, key=day_sums.get)
            ax.annotate(f'Busiest: {day_names[busiest_day]}', 
                       xy=(busiest_day, day_sums[busiest_day]),
                       xytext=(busiest_day, day_sums[busiest_day] * 1.1),
                       ha='center', fontsize=10,
                       bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.8))
    
    # Subtle grid
    ax.grid(True, linestyle='--', alpha=0.3, axis='y')
    
    # Customize legend
    ax.legend(title="Region", loc='upper right', fontsize=10, 
              title_fontsize=12, framealpha=0.7)
    
    # Add footer with info
    plt.figtext(0.5, 0.01, f"Data for past {days} days" + 
                (f" in {region}" if region else ""), 
                ha="center", fontsize=10, style='italic')
    
    return fig

def create_heatmap(data, regions, hours, title, days):
    """Create an improved heatmap with better styling."""
    # Create a matrix for the heatmap
    heatmap_data = np.zeros((len(regions), 24))
    
    # Fill in the data
    for item in data:
        region_idx = regions.index(item['serverid'])
        hour = item['hour_of_day']
        total_events = item['total_new_events']
        heatmap_data[region_idx, hour] = total_events
    
    # Create a custom colormap that transitions from white to blue to purple
    colors = [(1, 1, 1), (0.38, 0.51, 0.74), (0.4, 0.23, 0.72)]
    custom_cmap = LinearSegmentedColormap.from_list('discord_cmap', colors, N=256)
    
    # Create a plot
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Create the heatmap with improved colormap
    im = ax.imshow(heatmap_data, cmap=custom_cmap)
    
    # Add colorbar
    cbar = ax.figure.colorbar(im, ax=ax)
    cbar.ax.set_ylabel("Total New Events", rotation=-90, va="bottom")
    
    # Set ticks and labels
    ax.set_xticks(np.arange(24))
    ax.set_xticklabels(hours)
    ax.set_yticks(np.arange(len(regions)))
    ax.set_yticklabels(regions)
    
    # Add grid
    ax.set_xticks(np.arange(24+1)-0.5, minor=True)
    ax.set_yticks(np.arange(len(regions)+1)-0.5, minor=True)
    ax.grid(which="minor", color="gray", linestyle='-', linewidth=0.5, alpha=0.2)
    
    # Label the chart
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_xlabel("Hour of Day (UTC)", fontsize=12)
    ax.set_ylabel("Region", fontsize=12)
    
    # Create text annotations with improved visibility
    max_val = np.max(heatmap_data)
    for i in range(len(regions)):
        for j in range(24):
            value = heatmap_data[i, j]
            # Only show text if the value is significant
            if value > 0.1 * max_val:
                text_color = "white" if value > 0.5 * max_val else "black"
                ax.text(j, i, f"{value:.0f}",
                        ha="center", va="center", color=text_color,
                        fontsize=8, fontweight='bold')
    
    # Add footer with info
    plt.figtext(0.5, 0.01, f"Data for past {days} days", 
                ha="center", fontsize=10, style='italic')
    
    return fig

def create_comparison_bar_chart(comparison_data, title, days, region=None):
    """Create an improved comparison bar chart."""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    regions = list(comparison_data.keys())
    total_events = [comparison_data[r]['total_events'] for r in regions]
    notable_events = [comparison_data[r]['notable_events'] for r in regions]
    percentages = [comparison_data[r]['percentage_notable'] for r in regions]
    
    # Set up bar positions
    x = np.arange(len(regions))
    width = 0.35
    
    # Create bars with custom colors
    ax.bar(x - width/2, total_events, width, label='All Events', color=DISCORD_BLUE, alpha=0.7)
    ax.bar(x + width/2, notable_events, width, label='Notable Events', color=DISCORD_PURPLE, alpha=0.7)
    
    # Add percentage labels
    for i, v in enumerate(percentages):
        ax.text(i, max(total_events[i], notable_events[i]) + 1, 
                f"{v:.1f}%", ha='center', fontsize=10, fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.2", fc=DISCORD_YELLOW, ec="gray", alpha=0.7))
    
    # Format the plot
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_xlabel("Region", fontsize=12)
    ax.set_ylabel("Event Count", fontsize=12)
    ax.set_xticks(x)
    ax.set_xticklabels(regions)
    
    # Add subtle grid
    ax.grid(True, linestyle='--', alpha=0.3, axis='y')
    
    # Customize legend
    ax.legend(title="Event Type", loc='upper right', fontsize=10, 
              title_fontsize=12, framealpha=0.7)
    
    # Add footer with info
    plt.figtext(0.5, 0.01, f"Data for past {days} days" + 
                (f" in {region}" if region else ""), 
                ha="center", fontsize=10, style='italic')
    
    return fig 