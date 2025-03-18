import asyncio
import os
import json
from scrapybara import Scrapybara
from undetected_playwright.async_api import async_playwright


async def get_scrapybara_browser():
    client = Scrapybara(api_key=os.getenv("SCRAPYBARA_API_KEY"))
    instance = client.start_browser()
    return instance


async def process_menu_items(page):

    # Use a set to ensure no duplicates
    processed_ids = set()
    
    while True:
        # Scroll down by 720 pixels and wait for the new items to load.
        await page.evaluate("window.scrollBy(0, 720)")
        await page.wait_for_timeout(3000)  # Adjust delay as needed

        # Grab all menu items after scrolling
        menu_items = await page.query_selector_all('[data-anchor-id="MenuItem"]')

        # Process each menu item that has not been processed yet.
        for item in menu_items:
            item_id = await item.get_attribute("data-item-id")
            if not item_id:
                print("Menu Item ID not found")
                continue
            if item_id in processed_ids:
                # Skip if this item has already been processed.
                print("already processed")
                continue
            processed_ids.add(item_id)
            print(f"Menu Item ID: {item_id}")

            try:
                # Click the menu item and wait briefly.
                await item.click()
                print(f"Clicked on Menu Item ID: {item_id}")

                await page.wait_for_timeout(2000)  # Wait for modal content to load
                
                # Close the modal
                await page.keyboard.press("Escape")
                print(f"Closed Menu Item ID: {item_id}")

                await page.wait_for_timeout(2000)  # Wait for modal to close gracefully
            except Exception as e:
                print(f"Error processing Menu Item ID {item_id}: {e}")

        # Determine if we have reached the bottom of the page.
        scroll_position = await page.evaluate("window.scrollY")
        viewport_height = await page.evaluate("window.innerHeight")
        total_height = await page.evaluate("document.documentElement.scrollHeight")
        
        print(f"Scroll Position: {scroll_position}, Viewport Height: {viewport_height}, Total Height: {total_height}")
        
        # If the sum of the current scroll position and the viewport height is greater than or equal
        # to the total height of the document, then we've reached the bottom.
        if scroll_position + viewport_height >= total_height:
            print("Reached bottom of the page.")
            print(processed_ids)
            break


async def retrieve_menu_items(instance, start_url: str) -> list[dict]:
    """
    :args:
    instance: the scrapybara instance to use
    url: the initial url to navigate to

    :desc:
    this function navigates to {url}. then, it will collect the detailed
    data for each menu item in the store and return it.

    (hint: click a menu item, open dev tools -> network tab -> filter for
            "https://www.doordash.com/graphql/itemPage?operation=itemPage")

    one way to do this is to scroll through the page and click on each menu
    item.

    determine the most efficient way to collect this data.

    :returns:
    a list of menu items on the page, represented as dictionaries
    """

    complete_data = []

    cdp_url = instance.get_cdp_url().cdp_url
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(cdp_url)
        page = await browser.new_page()

        # browser automation ...

        await page.goto(start_url, wait_until="networkidle")
        await page.wait_for_selector('button.styles__ButtonRoot-sc-1ldytso-0', timeout=5000)
        await page.click('button.styles__ButtonRoot-sc-1ldytso-0')

        async def handle_response(response):
            # print('happened')
            if "https://www.doordash.com/graphql/itemPage?operation=itemPage" in response.url:
                try:
                    json_data = await response.json()
                    item_name = json_data.get("data", {}).get("itemPage", {}).get("itemHeader", {}).get("name", "Unknown Item")
                    print(f"Extracted Item: {item_name}")
                    complete_data.append(json_data.get("data", {}).get("itemPage", {}))
                except:
                    print("Failed to extract item from response")

        page.on("response", handle_response)


        await process_menu_items(page)
        # print(complete_data)
        return complete_data



async def main():
    instance = await get_scrapybara_browser()

    try:
        await retrieve_menu_items(
            instance,
            "https://www.doordash.com/store/panda-express-san-francisco-980938/12722988/?event_type=autocomplete&pickup=false",
        )
    finally:
        # Be sure to close the browser instance after you're done!
        instance.stop()


if __name__ == "__main__":
    asyncio.run(main())
