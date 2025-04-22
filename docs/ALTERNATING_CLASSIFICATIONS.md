# Alternating Classifications System for CTF Region

## Overview

The alternating classifications system allows the Comedy-Theatre-Film (CTF) region server to cycle through different event types on each API request. This maximizes the variety of events that can be discovered while still respecting Ticketmaster's rate limits.

## How It Works

1. Every 60 seconds, the CTF server makes an API request to Ticketmaster
2. Each request rotates through three classifications:
   - First request: Comedy events (Arts & Theatre + Comedy genre)
   - Second request: Theatre events (Arts & Theatre + Theatre genre)
   - Third request: Film events (Film + Miscellaneous genre with specific subtypes)
   - Fourth request: Back to Comedy events, and the cycle continues

## Classification IDs Used

The system rotates through these three Ticketmaster classifications:

| Request Cycle | Name | Classification ID | Genre ID | Additional Parameters | Description |
|---------------|------|-------------------|----------|------------------------|-------------|
| 1 | Comedy | KZFzniwnSyZfZ7v7na | KnvZfZ7vAe1 | None | Comedy events |
| 2 | Theatre | KZFzniwnSyZfZ7v7na | KnvZfZ7v7l1 | None | Theater/Broadway events |
| 3 | Film Events | KZFzniwnSyZfZ7v7nn | KnvZfZ7vAka | subGenreId=KZazBEonSMnZfZ7vFln, typeId=KZAyXgnZfZ7v7nI, subTypeId=KZFzBErXgnZfZ7v7lJ | Film events, including movies, screenings, and film festivals |

## Implementation Details

- The classification rotation is maintained in `api/alternating_events.py`
- Global state tracks the current position in the rotation
- Each request updates the position to the next in sequence
- The rotation only applies to the CTF region server; other regions maintain their specific classification focus
- Film events use additional Ticketmaster classification parameters (subGenreId, typeId, subTypeId) for more specific targeting

## Server Naming

The Comedy-Theatre-Film server is identified in the database using the ServerID "ctf". This represents the merger of the previous Comedy ("co") and Theatre ("th") servers into a single server with a rotating classification system.

## Adding More Classifications

To add more classifications to the rotation:

1. Open `api/alternating_events.py`
2. Add new entries to the `CLASSIFICATIONS` list, with:
   - `name`: A descriptive name for logging
   - `classification_id`: The Ticketmaster classification ID
   - `genre_id`: An optional genre ID to further filter results
   - `subgenre_id`: An optional subgenre ID for further filtering
   - `type_id`: An optional type ID for further filtering
   - `subtype_id`: An optional subtype ID for further filtering

## Ticketmaster Classification Reference

Main segment IDs:
- `KZFzniwnSyZfZ7v7nJ` - Music
- `KZFzniwnSyZfZ7v7na` - Arts & Theatre
- `KZFzniwnSyZfZ7v7nn` - Film
- `KZFzniwnSyZfZ7v7n1` - Miscellaneous
- `KZFzniwnSyZfZ7v7nE` - Sports

Common Genre IDs:
- `KnvZfZ7vAe1` - Comedy
- `KnvZfZ7v7l1` - Theatre
- `KnvZfZ7vAka` - Miscellaneous (Film)
- `KnvZfZ7vAeA` - Classical
- `KnvZfZ7vAvv` - Blues
- `KnvZfZ7vAev` - Pop

Subgenre, Type and Subtype IDs are specific to their parent categories. The Ticketmaster API Documentation provides more detailed information on these IDs. 