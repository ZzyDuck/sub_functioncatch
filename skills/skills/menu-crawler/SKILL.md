---
name: "menu-crawler"
description: "Crawls and extracts menu structures from web applications. Invoke when user needs to generate a menu tree from a web application URL with optional login credentials."
---

# Menu Crawler

This skill crawls web applications to extract their menu structures and generates a hierarchical menu tree in JSON format.

## What it does
- Extracts menu structures from web applications
- Supports login authentication
- Handles nested menus (up to 3 levels)
- Generates a structured JSON menu tree
- Optimized for SPA (Single Page Application) with hash-based routing

## When to invoke it
- When you need to generate a menu tree from a web application
- When you need to explore the navigation structure of a web application
- When you need to document the menu hierarchy of a web application

## Usage

To use this skill, run the menu crawler with the following parameters:

```bash
python .trae/skills/menu-crawler/menu_crawler.py <start_url> [username] [password]
```

### Parameters
- `start_url`: The URL to start crawling from (e.g., `http://example.com/app`)
- `username`: Optional login username
- `password`: Optional login password (if not provided, defaults to "Asiainfo1@3" for username "admin")

### Example
```bash
python .trae/skills/menu-crawler/menu_crawler.py http://10.28.149.50:9432/iam/v1/#/home/homeManage admin Asiainfo1@3
```

## Script Location

The `menu_crawler.py` script is located in the `.trae/skills/menu-crawler/` directory.

## Output

The crawler generates a `menu_tree.json` file in the `.trae/skills/menu-crawler/` directory with the extracted menu structure. The output format is a hierarchical JSON object with menu names, URLs, and nested children.

### Example output structure
```json
{
  "首页": {
    "url": "/home",
    "children": {
      "首页视图": {
        "url": "http://example.com/app/#/home",
        "children": {
          "首页": {
            "url": "http://example.com/app/#/home"
          }
        }
      }
    }
  }
}
```

## Features
- **Smart menu detection**: Automatically detects different types of menu structures
- **Login support**: Handles authentication for protected applications
- **Nested menu support**: Extracts up to 3 levels of nested menus
- **URL normalization**: Handles hash-based routing in SPA applications
- **Error handling**: Gracefully handles errors and continues crawling
- **Configurable wait times**: Optimized for dynamic content loading

## Dependencies
- Python 3.7+
- Playwright
- Asyncio

## Notes
- The crawler uses a headless browser to ensure all dynamic content is loaded
- It may take some time to crawl large applications with many menu items
- The generated menu tree is saved to `menu_tree.json` in the FunctionCatch directory
- For best results, ensure the target application is accessible and the login credentials are correct