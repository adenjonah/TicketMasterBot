# Category-Specific Servers

## Overview

The TicketMasterBot system includes specialized server instances dedicated to specific event categories: Comedy, Theatre, and Film. Each runs as a separate instance with its own specialized Ticketmaster API parameters to focus on a particular type of event.

## Server Categories

### 1. Comedy Server (co)

The Comedy server focuses exclusively on comedy events, including standup, improv, and other comedy performances.

- **Region ID**: `co`
- **Classification ID**: `KZFzniwnSyZfZ7v7na` (Arts & Theatre)
- **Genre ID**: `KnvZfZ7vAe1` (Comedy)
- **API Focus**: Comedy events within the Arts & Theatre classification

### 2. Theatre Server (th)

The Theatre server focuses on theatrical performances, including plays, musicals, and Broadway shows.

- **Region ID**: `th`
- **Classification ID**: `KZFzniwnSyZfZ7v7na` (Arts & Theatre)
- **Genre ID**: `KnvZfZ7v7l1` (Theatre)
- **API Focus**: Theatre events within the Arts & Theatre classification

### 3. Film Server (fi)

The Film server focuses on film events, including movie screenings, premieres, and film festivals.

- **Region ID**: `fi`
- **Classification ID**: `KZFzniwnSyZfZ7v7nn` (Film)
- **Genre ID**: `KnvZfZ7vAka` (Miscellaneous Film)
- **Additional Parameters**:
  - `subGenreId`: `KZazBEonSMnZfZ7vFln` (Miscellaneous)
  - `typeId`: `KZAyXgnZfZ7v7nI` (Undefined)
  - `subTypeId`: `KZFzBErXgnZfZ7v7lJ` (Undefined)
- **API Focus**: Film events with highly specific classification parameters

## Implementation Details

Each category server uses its own specialized API request parameters defined in the configuration. The Film server has additional implementation details in `api/film_events.py` to handle the more complex classification parameters needed for film events.

## Server Configuration

To run one of these category servers:

1. Set the `REGION` environment variable to one of: `comedy`, `theater`, or `film`
2. The system will automatically select the appropriate classification IDs and parameters
3. For Film servers, additional API parameters are automatically applied

## Database Schema

Events from these servers are stored with their respective region identifiers in the database:

- Comedy events: `region = 'co'`
- Theatre events: `region = 'th'` 
- Film events: `region = 'fi'`

This allows for proper filtering and organization of events by category type.

## Notification Display

When notifications are sent to Discord channels, events from these specialized servers will display their region in the footer:

- "Region: Comedy"
- "Region: Theater"
- "Region: Film"

This helps users identify the source and category of each event notification. 