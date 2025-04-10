# Auto for WeChat Publishing

An automated tool for publishing articles to WeChat Official Accounts.

## Features

- Convert Markdown articles to WeChat-compatible HTML
- Extract and process media files (images, etc.)
- Automatically publish to WeChat Official Account
- Support for metadata and styling

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/auto_for_wechat_publishing.git
cd auto_for_wechat_publishing
```

2. Install dependencies using Poetry:
```bash
poetry install
```

3. Create a `.env` file in the root directory with your WeChat credentials:
```env
WECHAT_APPID=your_app_id
WECHAT_SECRET=your_secret
```

## Usage

1. Place your article in Markdown format in `data/input/article.md`
2. Add any media files to `data/input/inserting_media/`
3. Run the main script:
```bash
poetry run python -m src.auto_for_wechat_publishing.main
```

## Project Structure

```
auto_for_wechat_publishing/
├── .env                  # Sensitive data (WeChat AppID, Secret)
├── config/
│   └── settings.ini      # Non-sensitive configuration
├── data/
│   ├── input/            # Input files
│   └── templates/        # CSS templates
├── src/
│   └── auto_for_wechat_publishing/
│       ├── content/      # Content processing
│       └── wechat/       # WeChat API interactions
└── tests/                # Test files
```

## Development

- Run tests: `poetry run pytest`
- Format code: `poetry run black .`
- Sort imports: `poetry run isort .`
- Lint code: `poetry run flake8`

## License

MIT License 