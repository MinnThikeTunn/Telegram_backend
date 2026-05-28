# Delivery Matrix API Documentation

This document provides detailed information about the Delivery Matrix API for web development coding agents.

---

## Overview

| Attribute | Value |
|-----------|-------|
| **Base URL** | `http://localhost:8000` |
| **API Version** | v1 |
| **Protocol** | HTTP |
| **Data Format** | JSON |

---

## Endpoints

### Get Delivery Matrix

Retrieves a paginated list of delivery matrix entries with optional search filtering.

```http
GET /api/v1/delivery-matrix
```

---

## Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `page` | integer | No | 1 | Page number for pagination |
| `limit` | integer | No | 10 | Number of records per page |
| `search` | string | No | (none) | Search filter for township name |

---

## Example Request

### cURL

```bash
curl -X GET \
  'http://localhost:8000/api/v1/delivery-matrix?page=1&limit=10&search=ma' \
  -H 'accept: application/json'
```

---

## Success Response

```json
{
  "data": [
    {
      "id": "ts_1",
      "township_name": "Kamayut",
      "region": "Yangon Region",
      "division": "Yangon West",
      "rate": 3000,
      "estimated_transit_timeline": "1-2 Days"
    }
  ],
  "pagination": {
    "total_records": 49,
    "current_page": 1,
    "limit": 10,
    "total_pages": 5,
    "has_next": true,
    "has_prev": false
  }
}
```

---

## Response Schema

### Data Array Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier for the delivery zone |
| `township_name` | string | Name of the township |
| `region` | string | Geographic region |
| `division` | string | Administrative division within the region |
| `rate` | integer | Delivery rate (in local currency) |
| `estimated_transit_timeline` | string | Expected delivery time (e.g., "1-2 Days") |

### Pagination Object Fields

| Field | Type | Description |
|-------|------|-------------|
| `total_records` | integer | Total number of matching records |
| `current_page` | integer | Current page number |
| `limit` | integer | Records per page |
| `total_pages` | integer | Total number of pages |
| `has_next` | boolean | Indicates if there is a next page |
| `has_prev` | boolean | Indicates if there is a previous page |

---

## HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success - Request completed successfully |
| 400 | Bad Request - Invalid query parameters |
| 404 | Not Found - Endpoint not available |
| 500 | Internal Server Error - Server-side error |

---

## Usage Notes for Developers

1. **Pagination**: Use `page` and `limit` parameters to navigate through large datasets
2. **Search**: The `search` parameter performs partial matching on the `township_name` field
3. **Rate Values**: The `rate` field contains integer values representing delivery fees
4. **Timeline**: The `estimated_transit_timeline` provides expected delivery duration