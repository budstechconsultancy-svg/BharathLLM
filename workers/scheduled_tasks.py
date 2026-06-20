import os
import logging
from pathlib import Path
from .celery_app import celery_app
from .tasks import ingest_pdf_task

logger = logging.getLogger("ScheduledScrapers")

@celery_app.task(bind=True, queue="scraping")
def scrape_finance_circulars(self):
    """
    Simulates a web scraper hitting gst.gov.in and incometaxindia.gov.in.
    If a new circular is found, saves it to the corpus directory and triggers ingestion.
    """
    logger.info("Starting scheduled midnight scrape for Finance Circulars...")
    
    # Mock finding a new circular
    new_circular_filename = "mock_gst_circular_today.pdf"
    target_dir = Path("pipeline/assets/finance_corpus/gst")
    target_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = target_dir / new_circular_filename
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("%PDF-1.4\nMock GST Circular PDF content downloaded at midnight.")
        
    logger.info(f"Successfully scraped new circular: {new_circular_filename}")
    
    # Trigger the ingestion worker asynchronously (does not block API)
    logger.info("Handing off to ingest_pdf_task...")
    ingest_pdf_task.delay(str(file_path), new_circular_filename, "Finance")
    
    return f"Scraped and triggered ingestion for {new_circular_filename}"

@celery_app.task(bind=True, queue="scraping")
def scrape_legal_judgements(self):
    """
    Simulates a web scraper hitting sci.gov.in for today's judgements.
    """
    logger.info("Starting scheduled midnight scrape for SC Judgements...")
    
    # Mock finding a new judgement
    new_judgement_filename = "mock_sc_judgement_today.pdf"
    target_dir = Path("pipeline/assets/legal_corpus/sc_judgements")
    target_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = target_dir / new_judgement_filename
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("%PDF-1.4\nMock SC Judgement PDF content downloaded at midnight.")
        
    logger.info(f"Successfully scraped new judgement: {new_judgement_filename}")
    
    # Trigger the ingestion worker asynchronously
    logger.info("Handing off to ingest_pdf_task...")
    ingest_pdf_task.delay(str(file_path), new_judgement_filename, "Legal")
    
    return f"Scraped and triggered ingestion for {new_judgement_filename}"
