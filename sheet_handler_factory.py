from typing import List, Any
from sheet_handler import SheetHandler
from sheet_handlers import (
    SDESheetHandler,
    CoreSheetHandler,
    LeetCodeDSA75Handler,
    LeetCodeSQLHandler,
    GFGMustDoProductHandler,
    MicrosoftDSAHandler,
    PhonePeDSAHandler,
    OracleDSAHandler,
    LinuxCommandsHandler,
    DockerCommandsHandler,
    DSACommonPatterns,
    LanggraphHandler
)

class SheetHandlerFactory:
    @staticmethod
    def create_handler(sheet_type: str) -> SheetHandler:
        if sheet_type == "sde_sheet":
            return SDESheetHandler()
        elif sheet_type in ["dbms_core_sheet", "os_core_sheet", "cn_core_sheet"]:
            subject = sheet_type.split("_")[0]
            return CoreSheetHandler(subject)
        elif sheet_type == "lc_sql_50":
            return LeetCodeSQLHandler()
        elif sheet_type == "must_do_product_gfg":
            return GFGMustDoProductHandler()
        elif sheet_type == "lc_dsa_75":
            return LeetCodeDSA75Handler()
        elif sheet_type == "microsoft_dsa":
            return MicrosoftDSAHandler()
        elif sheet_type == "phonepe_dsa":
            return PhonePeDSAHandler()
        elif sheet_type == "oracle_dsa":
            return OracleDSAHandler()
        elif sheet_type == "linux_commands":
            return LinuxCommandsHandler()
        elif sheet_type == "docker_commands":
            return DockerCommandsHandler()
        elif sheet_type == "langgraph":
            return LanggraphHandler()
        elif sheet_type == "dsa_common_patterns":
            return DSACommonPatterns()
        else:
            raise ValueError(f"Invalid sheet type: {sheet_type}")

    @staticmethod
    def get_sheet_type(sheet_types) -> List[str]:
        inp = input("Enter sheet type: ")
        if inp == "random":
            return sheet_types
        if inp.isdigit():
            return [sheet_types[int(inp)]]
        else:
            return [sheet for sheet in sheet_types if inp in sheet]
