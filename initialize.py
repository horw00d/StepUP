import logging
import sys
import time
from initialization import ingest, generate_assets

#verbose logging to print to the terminal
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

def run_setup():
    logging.info("==================================================")
    logging.info("Starting StepUP Platform Initialization")
    logging.info("==================================================")
    t0 = time.time()

    try:
        logging.info("\n[Phase 1/2] Ingesting raw StepUP-P150 data into SQLite...")
        # Call the main function from your ingest script
        ingest.run_ingest() 

        logging.info("\n[Phase 2/2] Generating static peak pressure assets...")
        # Call the main function from your asset generator
        #generate_assets.generate_assets()

        t1 = time.time()
        logging.info("\n==================================================")
        logging.info(f"Initialization Complete in {t1-t0:.2f} seconds.")
        logging.info("You may now launch the platform by running: python app.py")
        logging.info("==================================================")
        
    except Exception as e:
        logging.error(f"Initialization failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_setup()