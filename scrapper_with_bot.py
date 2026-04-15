import asyncio
import re
import os
import sys
from playwright.async_api import async_playwright
from telegram import Bot
from dotenv import load_dotenv

# es - Carga variables de entorno desde .env
# en - Load environment variables from .env
load_dotenv()

TELEGRAM_TOKEN     = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID")

URL = "https://entradas.roigarena.com/roigarena/select/2801703?sessionPreviewToken=AK6G3EN576M3M2OX&viewCode=V_blockmap_view"


# es - Validar configuración
# en - Validate configuration
def validate_configuration():
    errores = []
    if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == "PON_AQUI_TU_TOKEN":
        errores.append("  ❌ TELEGRAM_TOKEN no configurado en .env")
    if not TELEGRAM_CHAT_ID or TELEGRAM_CHAT_ID == "PON_AQUI_TU_CHAT_ID":
        errores.append("  ❌ TELEGRAM_CHAT_ID no configurado en .env")
    if errores:
        print("\n⚠️  Errores de configuración en el fichero .env:")
        for e in errores:
            print(e)
        sys.exit(1)
    print("✅ Configuración cargada correctamente desde .env")


# es - Enviar mensaje a Telegram
# en - Send message to Telegram
async def send_telegram(mensaje: str):
    bot = Bot(token=TELEGRAM_TOKEN)
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=mensaje, parse_mode="HTML")
    print("📨 Telegram enviado")


# es - Obtener entradas disponibles de la página, con manejo de cookies y contenido dinámico
# en - Obtain available tickets from the page, with cookie handling and dynamic content
async def obtain_tickets() -> list[tuple[str, str]]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        print(f"🔗 Abriendo página: {URL}")
        await page.goto(URL, wait_until="domcontentloaded", timeout=30000)

        # es - Aceptar cookies
        # en - Accept cookies
        try:
            boton = await page.wait_for_selector("text=Aceptar todas", timeout=8000)
            await boton.click()
            print("✅ Cookies aceptadas")
            await page.wait_for_timeout(1500)
        except Exception:
            print("ℹ️  Banner de cookies no apareció")

        # es - Esperar carga dinámica
        # en - Wait for dynamic loading
        await page.wait_for_timeout(5000)
        try:
            await page.wait_for_selector(
                "[class*='block'], [class*='sector'], [class*='area'], svg",
                timeout=15000
            )
        except Exception:
            pass

        contenido = await page.inner_text("body")
        await browser.close()

    # es - Buscar patrón "Nombre - N entradas disponibles"
    # en - Search for pattern "Name - N tickets available"
    patron = re.compile(
        r"([^\n\r\t]{2,80}?)\s*[-–—]\s*(\d+)\s+entradas?\s+disponibles?",
        re.IGNORECASE
    )
    resultados = patron.findall(contenido)

    # es - Fallback: solo número
    # en - Fallback: only number
    if not resultados:
        patron_simple = re.compile(r"(\d+)\s+entradas?\s+disponibles?", re.IGNORECASE)
        numeros = patron_simple.findall(contenido)
        resultados = [("Zona desconocida", n) for n in numeros]

    return resultados

# es - Ejecutar consulta y enviar notificación si hay entradas
# en - Execute query and send notification if there are tickets
async def execute_query():
    validate_configuration()

    print("🤖 Bot iniciado (modo ejecución única)")
    print("="*50)

    resultados = await obtain_tickets()

    print("\n       ENTRADAS DISPONIBLES")
    print("="*50)

    if resultados:
        for nombre, numero in resultados:
            print(f"  🎟️  {nombre.strip()} - {numero} entradas disponibles")

        lineas = "\n".join(
            f"🎟️ <b>{n.strip()}</b> — {num} entradas disponibles"
            for n, num in resultados
        )
        mensaje = f"🚨 <b>¡Entradas disponibles!</b>\n\n{lineas}\n\n🔗 <a href='{URL}'>Comprar aquí</a>"
        await send_telegram(mensaje)
    else:
        print("  ❌ No hay entradas disponibles en este momento")

    print("="*50)
    print("✅ Ejecución completada")


if __name__ == "__main__":
    asyncio.run(execute_query())