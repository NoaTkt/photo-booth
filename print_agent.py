import os

import win32api
import win32con
import win32gui
import win32print
import win32ui
from PIL import Image, ImageWin


class PrintAgent:
    def __init__(self, printer_name: str | None = None):
        self.printer_name = printer_name or self.get_default_printer()
        self.orientation = "Portrait"  # "Portrait" ou "Paysage"

    def get_installed_printers(self) -> list[str]:
        flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        printers = [printer[2] for printer in win32print.EnumPrinters(flags)]
        return printers

    def get_default_printer(self) -> str | None:
        try:
            return win32print.GetDefaultPrinter()
        except Exception:
            return None

    def print_photo(self, file_path: str, printer_name: str | None = None) -> None:
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"Fichier introuvable : {file_path}")

        printer = printer_name or self.printer_name
        if not printer:
            raise RuntimeError("Aucune imprimante detectee")

        try:
            # Ouvrir l'imprimante et récupérer les paramètres
            hPrinter = win32print.OpenPrinter(printer)
            try:
                pinfo = win32print.GetPrinter(hPrinter, 2)
                devmode = pinfo.get("pDevMode")
                if devmode:
                    if self.orientation == "Paysage":
                        devmode.Orientation = win32con.DMORIENT_LANDSCAPE
                    else:
                        devmode.Orientation = win32con.DMORIENT_PORTRAIT

                    raw_hdc = win32gui.CreateDC(
                        pinfo["pDriverName"],
                        pinfo["pPrinterName"],
                        devmode,
                    )
                    hDC = win32ui.CreateDCFromHandle(raw_hdc)
                else:
                    hDC = win32ui.CreateDC()
                    hDC.CreatePrinterDC(printer)
            finally:
                win32print.ClosePrinter(hPrinter)

            hDC.StartDoc(file_path)
            hDC.StartPage()

            bmp = Image.open(file_path)
            if bmp.mode != "RGB":
                bmp = bmp.convert("RGB")

            printable_area = (
                hDC.GetDeviceCaps(win32con.HORZRES),
                hDC.GetDeviceCaps(win32con.VERTRES),
            )
            
            bmp_ratio = bmp.width / bmp.height
            area_ratio = printable_area[0] / printable_area[1]
            zoom_factor = 1.04
            if bmp_ratio > area_ratio:
                scaled_width = int(printable_area[0] * zoom_factor)
                scaled_height = int(scaled_width / bmp_ratio)
            else:
                scaled_height = int(printable_area[1] * zoom_factor)
                scaled_width = int(scaled_height * bmp_ratio)

            x = int((printable_area[0] - scaled_width) / 2)
            y = int((printable_area[1] - scaled_height) / 2)

            dib = ImageWin.Dib(bmp)
            dib.draw(hDC.GetHandleOutput(), (x, y, x + scaled_width, y + scaled_height))

            hDC.EndPage()
            hDC.EndDoc()
            hDC.DeleteDC()
        except Exception as error:
            raise RuntimeError(f"Erreur d'impression : {error}")
