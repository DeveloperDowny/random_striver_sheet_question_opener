import random
import logging
from sheet_handler_factory import SheetHandlerFactory


logger = logging.getLogger()

def main():
    logger.info("Script started.")
    sheet_types = [
        "sde_sheet",
        "dbms_core_sheet",
        "os_core_sheet",
        "cn_core_sheet",
        "lc_sql_50",
        "must_do_product_gfg",
        "lc_dsa_75",
        "microsoft_dsa",
        "phonepe_dsa",
        "oracle_dsa",
        "linux_commands",
        "docker_commands",
        "dsa_common_patterns",
    ]
    filtered_sheet_types = SheetHandlerFactory.get_sheet_type(sheet_types)
    sheet_type = random.choice(filtered_sheet_types)
    handler = SheetHandlerFactory.create_handler(sheet_type)
    handler.process()

    logger.info("Script finished.")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler("debug.log"), logging.StreamHandler()],
    )
    main()
