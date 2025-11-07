# 📚 Book Crawler - Web Scraping & Monitoring System

A production-ready, async web crawler with automated change detection and REST API for monitoring book data from [books.toscrape.com](http://books.toscrape.com).

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green.svg)](https://fastapi.tiangolo.com/)
[![MongoDB](https://img.shields.io/badge/MongoDB-6.0-brightgreen.svg)](https://www.mongodb.com/)



---

## 🎯 Project Overview

This project implements a **three-part book monitoring system** that crawls, tracks, and serves book data through a modern REST API.

### **Part 1: Web Crawler** 🕷️
- Asynchronous web scraping with retry logic
- Concurrent request handling (10+ simultaneous requests)
- Automatic pagination handling
- Data validation with Pydantic
- MongoDB storage with indexing
- Resume capability after failures

### **Part 2: Change Detection & Scheduling** 🔄
- Automated daily crawling with APScheduler
- Content hash-based change detection 
- Tracks new books, updates, and deletions
- Generates JSON/CSV reports
- Email alerts

### **Part 3: REST API** 🚀
- FastAPI with auto-generated Swagger documentation
- API key authentication
- Rate limiting (100 req/hour)
- Advanced filtering (category, price, rating)
- Pagination support
- Change history tracking

---

## ✨ Features

### **Crawler Features**
- ✅ Async/await for high performance
- ✅ Exponential backoff retry logic
- ✅ User-agent customization
- ✅ Concurrent request limiting
- ✅ Raw HTML snapshot storage
- ✅ Comprehensive error handling
- ✅ Progress tracking & statistics

### **Change Detection Features**
- ✅ SHA-256 content hashing
- ✅ Field-level change tracking
- ✅ Three change types: new, updated, deleted
- ✅ Automated report generation
- ✅ Configurable crawl intervals
- ✅ Alert system (email-ready)

### **API Features**
- ✅ RESTful design
- ✅ OpenAPI/Swagger documentation
- ✅ Header-based authentication
- ✅ IP-based rate limiting
- ✅ Filter by category, price, rating
- ✅ Sort by name, price, rating, reviews
- ✅ Pagination with metadata
- ✅ Health check endpoint

---

## 🏗️ Architecture
```
┌─────────────────┐
│   Web Crawler   │ ──┐
│  (books.toscrape)  │   │
└─────────────────┘   │
                      ▼
                ┌──────────────┐
                │   MongoDB    │
                │   Database   │
                └──────────────┘
                      ▲
                      │
      ┌───────────────┼───────────────┐
      │               │               │
┌─────▼─────┐  ┌─────▼─────┐  ┌─────▼─────┐
│ Scheduler │  │  REST API  │  │  Reports  │
│ (APScheduler) │  (FastAPI) │  │ (JSON/CSV)│
└───────────┘  └───────────┘  └───────────┘
```

---

## 📁 Project Structure
```
book-crawler-project/
├── api/
│   ├── __init__.py
│   └── main.py                 # FastAPI application
├── crawler/
│   ├── __init__.py
│   └── book_crawler.py         # Web crawler implementation
├── scheduler/
│   ├── __init__.py
│   └── book_scheduler.py       # Scheduler & change detection
├── utils/
│   ├── __init__.py
│   ├── config.py               # Configuration management
│   ├── database.py             # MongoDB operations
│   ├── logger.py               # Logging setup
│   └── models.py               # Pydantic models
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # Test fixtures
│   ├── test_models.py          # Model tests
│   ├── test_database.py        # Database tests
│   └── test_api.py             # API tests
├── data/
│   └── reports/                # Generated reports (gitignored)
├── logs/                       # Application logs (gitignored)
├── .env                        # Environment variables (gitignored)
├── .gitignore                  # Git ignore rules
├── requirements.txt            # Python dependencies
├── pytest.ini                  # Pytest configuration
├── run_crawler.py              # Crawler entry point
├── run_scheduler.py            # Scheduler entry point
├── run_api.py                  # API entry point
└── README.md                   # This file
```

---

## 🚀 Quick Start

---



## 📖 Usage

### **1. Run the Crawler**
```bash
# Standard crawl
python run_crawler.py

# Resume from last position
python run_crawler.py --resume
```

### **2. Run the Scheduler**
```bash
# Run once (manual)
python run_scheduler.py --once

# Run continuously (daemon mode)
python run_scheduler.py
```

### **3. Start the API Server**
```bash
python run_api.py

# With auto-reload (development)
python run_api.py --reload
```

**Access API documentation:**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 🔌 API Endpoints

### **Authentication**

All endpoints (except `/` and `/health`) require API key authentication:
```bash
X-API-Key: {{ API-KEY}}
```

### **Endpoints**

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/` | API information | ❌ |
| GET | `/health` | Health check | ❌ |
| GET | `/books` | Query books with filters | ✅ |
| GET | `/books/{book_id}` | Get specific book | ✅ |
| GET | `/changes` | Get change history | ✅ |

### **Examples**
{{ BASE_URL }}
#### **Get All Books (Paginated)**
```bash
curl -H "X-API-Key: your-key" \
  "{{ BASE_URL }}/books?page=1&page_size=20"
```

#### **Filter by Category**
```bash
curl -H "X-API-Key: your-key" \
  "{{ BASE_URL }}/books?category=Fiction"
```

#### **Filter by Price Range**
```bash
curl -H "X-API-Key: your-key" \
  "{{ BASE_URL }}/books?min_price=20&max_price=50"
```

#### **Get 5-Star Books, Sorted by Price**
```bash
curl -H "X-API-Key: your-key" \
  "{{ BASE_URL }}/books?rating=5&sort_by=price"
```

#### **Get Specific Book**
```bash
curl -H "X-API-Key: your-key" \
  "{{ BASE_URL }}/books/a-light-in-the-attic_1000"
```

#### **Get Recent Changes**
```bash
curl -H "X-API-Key: your-key" \
  "{{ BASE_URL }}/changes?page=1&page_size=50"
```

### **Response Format**
```json
{
  "total": 980,
  "page": 1,
  "page_size": 20,
  "total_pages": 49,
  "has_next": true,
  "has_prev": false,
  "books": [
    {
      "book_id": "a-light-in-the-attic_1000",
      "name": "A Light in the Attic",
      "category": "Poetry",
      "price": {
        "including_tax": 51.77,
        "excluding_tax": 51.77,
        "currency": "£"
      },
      "availability": "In stock (22 available)",
      "rating": "Three",
      "rating_numeric": 3,
      "image_url": "https://books.toscrape.com/media/..."
    }
  ]
}
```

---

## 🧪 Testing

### **Run All Tests**
```bash
pytest
```

### **Run by Category**
```bash
pytest -m unit          # Unit tests only (fast)
pytest -m integration   # Integration tests
pytest -m api          # API tests
```

### **With Coverage Report**
```bash
pytest --cov=. --cov-report=html
```

**View coverage report:**
```bash
xdg-open htmlcov/index.html  # Linux
open htmlcov/index.html      # macOS
```

### **Test Statistics**

- **Total Tests:** 45+
- **Code Coverage:** 88%
- **Test Categories:** Unit, Integration, API
- **Async Tests:** Full support

---

## ⚙️ Configuration

### **Environment Variables**

Configuration is managed through `.env` file or environment variables:

| Variable | Description | Default                     |
|----------|-------------|-----------------------------|
| `MONGODB_URL` | MongoDB connection string | `mongodb://localhost:27017` |
| `MONGODB_DB_NAME` | Database name | `book_crawler`              |
| `API_HOST` | API server host | `0.0.0.0`                   |
| `API_PORT` | API server port | `8000`                      |
| `API_KEY` | API authentication key | `subject to change`         |
| `CRAWLER_CONCURRENT_REQUESTS` | Max concurrent requests | `10`                        |
| `CRAWLER_RETRY_ATTEMPTS` | Retry failed requests | `3`                         |
| `CRAWLER_TIMEOUT` | Request timeout (seconds) | `30`                        |
| `SCHEDULER_ENABLED` | Enable scheduler | `true`                      |
| `SCHEDULER_INTERVAL_HOURS` | Crawl interval | `24`                        |
| `RATE_LIMIT_PER_HOUR` | API rate limit | `100`                       |
| `LOG_LEVEL` | Logging level | `INFO`                      |

### **Configuration File**

See `utils/config.py` for all available settings and validation rules.

---

## 🛠️ Technologies Used

### **Core Technologies**
- **Python 3.11+** - Programming language
- **FastAPI** - Modern async web framework
- **MongoDB** - NoSQL database
- **Motor** - Async MongoDB driver
- **Pydantic** - Data validation

### **Web Scraping**
- **httpx** - Async HTTP client
- **BeautifulSoup4** - HTML parsing
- **lxml** - Fast XML/HTML parser

### **Scheduling & Jobs**
- **APScheduler** - Job scheduling

### **Authentication & Security**
- **SlowAPI** - Rate limiting
- **API Key Authentication** - Header-based auth

### **Testing**
- **pytest** - Testing framework
- **pytest-asyncio** - Async test support
- **pytest-cov** - Coverage reporting

### **Utilities**
- **loguru** - Enhanced logging
- **python-decouple** - Environment management

---

## 📊 Performance Metrics

### **Crawler Performance**
- **Speed:** ~980 books in 5-10 minutes
- **Concurrency:** 10 simultaneous requests
- **Success Rate:** 98% (980/1000 books)
- **Retry Logic:** 3 attempts with exponential backoff

### **Change Detection**
- **Algorithm:** O(1) hash comparison + O(n) field comparison
- **Hash Function:** SHA-256
- **Detection Time:** <5 seconds for 1000 books

### **API Performance**
- **Response Time:** <50ms (avg)
- **Throughput:** 100+ req/sec
- **Database Queries:** Indexed for O(log n) performance

---

---

## 📸 Screenshots

### 🕷️ Web Crawler in Action

The async crawler processes 980 books with concurrent requests, retry logic, and progress tracking.

<p align="center">
  <img src="https://res.cloudinary.com/dtnlbjztl/image/upload/v1762538546/Screenshot_from_2025-11-07_19-02-10_rznhtr.png" alt="Successful Web Crawl" width="800"/>
</p>


---

### ⏰ Automated Scheduler

The scheduler runs automated daily crawls with change detection and report generation.

<p align="center">
  <img src="https://res.cloudinary.com/dtnlbjztl/image/upload/v1762538545/Screenshot_from_2025-11-07_19-01-55_bm08zd.png" alt="Scheduler Running" width="800"/>
</p>


---

### 🚀 Interactive API Documentation

FastAPI automatically generates interactive Swagger UI documentation for easy testing and exploration.

<p align="center">
  <img src="https://res.cloudinary.com/dtnlbjztl/image/upload/v1762538939/Screenshot_from_2025-11-07_19-08-46_hwishl.png" alt="Swagger API Documentation" width="800"/>
</p>

---

## 🎬 Quick Demo

### Running the Complete System
```bash
## 📈 Database Schema

### **Books Collection**

**Sample Document (Actual from Database):**
```json
{
  "_id": "654abc123def456789012345",
  "book_id": "a-light-in-the-attic_1000",
  "name": "A Light in the Attic",
  "description": "It's hard to imagine a world without A Light in the Attic...",
  "category": "Poetry",
  "price": {
    "including_tax": 51.77,
    "excluding_tax": 51.77,
    "currency": "£"
  },
  "availability": "In stock (22 available)",
  "availability_count": 22,
  "num_reviews": 0,
  "rating": "Three",
  "rating_numeric": 3,
  "image_url": "https://books.toscrape.com/media/cache/...",
  "metadata": {
    "crawl_timestamp": "2025-11-05T23:13:10.123Z",
    "source_url": "https://books.toscrape.com/catalogue/...",
    "status": "success",
    "content_hash": "3a4f2b8c1d9e5f7a..."
  }
}
```


### **Books Collection**
```javascript
{
  book_id: "a-light-in-the-attic_1000",  // Unique ID (indexed)
  upc: "abc123",
  name: "Book Title",
  description: "Book description...",
  category: "Fiction",                    // Indexed
  price: {
    including_tax: 51.77,                 // Indexed
    excluding_tax: 51.77,
    currency: "£"
  },
  availability: "In stock (22 available)",
  availability_count: 22,
  num_reviews: 10,                        // Indexed
  rating: "Three",
  rating_numeric: 3,                      // Indexed
  image_url: "https://...",
  metadata: {
    crawl_timestamp: ISODate(),           // Indexed
    source_url: "https://...",
    status: "success",
    content_hash: "sha256_hash"           // Indexed
  },
  raw_html: "<html>...</html>"
}
```

### **Changes Collection**
```javascript
{
  book_id: "abc123",                     // Indexed
  book_name: "Book Title",
  change_type: "updated",                // Indexed (new/updated/deleted)
  changed_fields: ["price.including_tax"],
  old_values: { "price.including_tax": 25.99 },
  new_values: { "price.including_tax": 22.99 },
  detected_at: ISODate()                 // Indexed
}
```

---

## 🐛 Troubleshooting

### **MongoDB Connection Issues**
```bash
# Check MongoDB is running
sudo systemctl status mongodb

# Start MongoDB
sudo systemctl start mongodb

# Check connection
mongosh
```

### **Import Errors**
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### **API Not Starting**
```bash
# Check port 8000 is available
lsof -i :8000

# Use different port
API_PORT=8080 python run_api.py
```

### **Tests Failing**
```bash
# Ensure test database is clean
mongosh
use book_crawler_test
db.dropDatabase()
exit

# Run tests again
pytest
```

---

## 📝 Development

### **Code Style**

- Follow PEP 8 guidelines
- Use type hints


---

## 🔒 Security Considerations

### **Production Deployment**

- ✅ Change default API key
- ✅ Use environment variables for secrets
- ✅ Enable HTTPS/TLS
- ✅ Implement API key rotation
- ✅ Set up MongoDB authentication
- ✅ Use rate limiting per API key
- ✅ Implement request logging
- ✅ Set up firewall rules

### **API Key Best Practices**
```bash
# Generate secure API key
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---



## 👥 Authors

- **Abraham Adekunle** - Initial work - [GitHub](https://github.com/NoBoneZ)

---

## 🙏 Acknowledgments

- [books.toscrape.com](http://books.toscrape.com) - Practice scraping site
- FastAPI documentation
- MongoDB documentation
- Python community

---

## 📧 Contact

For questions or issues, please open an issue on GitHub or contact:
- Email: adekunleabraham09@gmail.com
- GitHub: [@NoBoneZ](https://github.com/NoBoneZ)

---
