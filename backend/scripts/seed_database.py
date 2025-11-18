"""
Script to seed the database with sample news articles.
Run this to populate your database for testing.

Usage:
    python scripts/seed_database.py
"""

import asyncio
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
import random

# Sample news articles for testing
SAMPLE_ARTICLES = [
    {
        "title": "Global Climate Summit 2024 Reaches Historic Agreement",
        "content": "World leaders gathered at the Global Climate Summit reached a groundbreaking agreement to reduce carbon emissions by 50% by 2030. The United Nations Secretary-General praised the unprecedented cooperation between developed and developing nations. Key commitments include increased funding for renewable energy and phasing out coal power plants.",
        "summary": "Historic climate agreement reached at UN summit with 50% emission reduction targets.",
        "url": "https://example.com/climate-summit-2024",
        "keywords": ["climate change", "united nations", "carbon emissions", "renewable energy", "global warming", "environment"],
        "source": "World News",
        "entities": {
            "persons": [],
            "locations": ["United Nations"],
            "organizations": ["UN", "United Nations"],
            "dates": ["2024", "2030"],
            "misc": []
        }
    },
    {
        "title": "Tech Giants Announce AI Safety Partnership",
        "content": "Major technology companies including Google, Microsoft, and OpenAI announced a new partnership focused on artificial intelligence safety and ethics. The collaboration aims to establish industry standards for responsible AI development. Researchers will share findings on potential risks and mitigation strategies.",
        "summary": "Google, Microsoft, OpenAI form partnership for AI safety standards.",
        "url": "https://example.com/ai-safety-partnership",
        "keywords": ["artificial intelligence", "ai safety", "technology", "google", "microsoft", "openai", "machine learning"],
        "source": "Tech Daily",
        "entities": {
            "persons": [],
            "locations": [],
            "organizations": ["Google", "Microsoft", "OpenAI"],
            "dates": [],
            "misc": []
        }
    },
    {
        "title": "Federal Reserve Maintains Interest Rates Amid Economic Uncertainty",
        "content": "The Federal Reserve announced its decision to maintain current interest rates, citing mixed economic signals. Inflation remains above the 2% target while employment figures show resilience. Economists predict potential rate cuts in the second half of the year if inflation continues to moderate.",
        "summary": "Fed holds rates steady as inflation remains above target.",
        "url": "https://example.com/fed-interest-rates",
        "keywords": ["federal reserve", "interest rates", "inflation", "economy", "monetary policy", "employment"],
        "source": "Financial Times",
        "entities": {
            "persons": [],
            "locations": ["United States"],
            "organizations": ["Federal Reserve"],
            "dates": [],
            "misc": []
        }
    },
    {
        "title": "SpaceX Successfully Launches Starship for Mars Mission Test",
        "content": "SpaceX completed a successful test flight of its Starship rocket, bringing humanity closer to Mars exploration. Elon Musk announced plans for the first crewed mission within three years. NASA has partnered with SpaceX for the Artemis program's lunar lander development.",
        "summary": "Starship test success advances Mars mission timeline.",
        "url": "https://example.com/spacex-starship-launch",
        "keywords": ["spacex", "starship", "mars", "space exploration", "elon musk", "nasa", "rocket", "artemis"],
        "source": "Space News",
        "entities": {
            "persons": ["Elon Musk"],
            "locations": ["Mars"],
            "organizations": ["SpaceX", "NASA"],
            "dates": [],
            "misc": ["Starship", "Artemis"]
        }
    },
    {
        "title": "Healthcare Reform Bill Passes Senate Vote",
        "content": "The Senate passed a comprehensive healthcare reform bill aimed at reducing prescription drug costs and expanding Medicare coverage. The legislation includes provisions for negotiating drug prices directly with pharmaceutical companies. Implementation is expected to begin in 2025.",
        "summary": "Senate approves healthcare bill targeting drug prices and Medicare expansion.",
        "url": "https://example.com/healthcare-reform-senate",
        "keywords": ["healthcare", "senate", "medicare", "prescription drugs", "reform", "pharmaceutical", "legislation"],
        "source": "Political News",
        "entities": {
            "persons": [],
            "locations": ["United States"],
            "organizations": ["Senate", "Medicare"],
            "dates": ["2025"],
            "misc": []
        }
    },
    {
        "title": "Electric Vehicle Sales Surpass Expectations in Q3",
        "content": "Electric vehicle sales exceeded analyst predictions with a 40% increase compared to the previous quarter. Tesla maintained market leadership while newcomers like Rivian and Lucid gained significant ground. Government incentives and expanding charging infrastructure contributed to the surge.",
        "summary": "EV sales jump 40% as market competition intensifies.",
        "url": "https://example.com/ev-sales-q3",
        "keywords": ["electric vehicles", "tesla", "ev", "automotive", "rivian", "lucid", "charging infrastructure"],
        "source": "Auto Industry Report",
        "entities": {
            "persons": [],
            "locations": [],
            "organizations": ["Tesla", "Rivian", "Lucid"],
            "dates": ["Q3"],
            "misc": []
        }
    },
    {
        "title": "Cybersecurity Breach Affects Millions of Users",
        "content": "A major cybersecurity incident at a leading financial services company exposed personal data of approximately 5 million customers. The breach included names, social security numbers, and account information. The company is offering free credit monitoring services to affected users.",
        "summary": "Financial services breach exposes 5 million customers' personal data.",
        "url": "https://example.com/cybersecurity-breach",
        "keywords": ["cybersecurity", "data breach", "privacy", "financial services", "security", "personal data", "hacking"],
        "source": "Security News",
        "entities": {
            "persons": [],
            "locations": [],
            "organizations": [],
            "dates": [],
            "misc": []
        }
    },
    {
        "title": "Renewable Energy Investment Hits Record High",
        "content": "Global investment in renewable energy reached a record $500 billion in 2024, with solar and wind projects leading the growth. China and the United States remain the top investors. Analysts predict continued expansion as costs decline and government policies favor clean energy.",
        "summary": "Renewable energy investment reaches $500B milestone.",
        "url": "https://example.com/renewable-investment-record",
        "keywords": ["renewable energy", "solar", "wind", "investment", "clean energy", "climate", "sustainability"],
        "source": "Energy Report",
        "entities": {
            "persons": [],
            "locations": ["China", "United States"],
            "organizations": [],
            "dates": ["2024"],
            "misc": []
        }
    },
    {
        "title": "New COVID-19 Variant Detected in Multiple Countries",
        "content": "Health officials are monitoring a newly identified COVID-19 variant detected in several countries. The World Health Organization has classified it as a variant of interest. Preliminary studies suggest current vaccines remain effective, though booster shots are recommended.",
        "summary": "WHO monitors new COVID variant; vaccines remain effective.",
        "url": "https://example.com/covid-new-variant",
        "keywords": ["covid-19", "coronavirus", "variant", "who", "vaccines", "pandemic", "health", "booster"],
        "source": "Health News",
        "entities": {
            "persons": [],
            "locations": [],
            "organizations": ["World Health Organization", "WHO"],
            "dates": [],
            "misc": ["COVID-19"]
        }
    },
    {
        "title": "Supreme Court to Hear Major Tech Antitrust Case",
        "content": "The Supreme Court agreed to hear arguments in a landmark antitrust case against major technology companies. The case could reshape how digital marketplaces operate and impact companies like Amazon and Apple. Consumer advocacy groups have praised the decision while tech industry representatives express concern.",
        "summary": "Supreme Court takes on tech antitrust case affecting digital marketplaces.",
        "url": "https://example.com/supreme-court-tech-antitrust",
        "keywords": ["supreme court", "antitrust", "technology", "amazon", "apple", "regulation", "monopoly", "digital marketplace"],
        "source": "Legal News",
        "entities": {
            "persons": [],
            "locations": ["United States"],
            "organizations": ["Supreme Court", "Amazon", "Apple"],
            "dates": [],
            "misc": []
        }
    }
]


async def seed_database():
    """Seed the database with sample articles."""
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["keyword_recommendation"]

    # Clear existing articles (optional)
    await db.news_articles.delete_many({})

    # Insert sample articles with timestamps
    for i, article in enumerate(SAMPLE_ARTICLES):
        article["created_at"] = datetime.utcnow()
        article["updated_at"] = datetime.utcnow()
        article["published_date"] = datetime.utcnow() - timedelta(days=random.randint(1, 30))

    result = await db.news_articles.insert_many(SAMPLE_ARTICLES)
    print(f"Inserted {len(result.inserted_ids)} sample articles")

    # Create indexes
    await db.news_articles.create_index([
        ("title", "text"),
        ("content", "text"),
        ("keywords", "text")
    ])
    await db.news_articles.create_index([("keywords", 1)])
    print("Created indexes")

    client.close()
    print("Database seeded successfully!")


if __name__ == "__main__":
    asyncio.run(seed_database())
