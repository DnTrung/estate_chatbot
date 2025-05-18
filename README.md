# Real Estate AI Assistant

A sophisticated AI-powered chatbot application designed to assist users in finding and managing real estate properties. This application combines natural language processing with a user-friendly graphical interface to provide personalized real estate assistance.

## Features

- Interactive GUI for easy property search and management
- AI-powered chatbot that understands natural language queries
- User context persistence across sessions
- Document processing capabilities (Word and PDF)
- Property data analysis and filtering
- Comprehensive logging system

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Required Python packages (see below)

### Installation

1. Clone the repository
2. Install the required dependencies:
```bash
pip install pandas tkinter PyPDF2 python-docx
```

### Running the Application

Simply run the main application file:
```bash
python main.py
```

## Project Structure

- `main.py`: Main application file containing the GUI and core functionality
- `chatbot.py`: AI chatbot implementation
- `user_context_db.py`: Database handling for user context and preferences
- `data_prepare.py`: Data preprocessing utilities
- `data/`: Directory containing property data
- `chatbot.log`: Application log file
- `user_context.db`: SQLite database for user context

## Usage

1. Launch the application
2. Use the chat interface to ask questions about properties
3. Upload documents for analysis
4. Save and load search preferences

## Technical Details

### Core Technologies

- Python 3.8+
- Tkinter for GUI
- Pandas for data processing
- SQLite for user context storage
- PyPDF2 and python-docx for document processing

### Logging

The application uses a dual logging system that writes to both console and `chatbot.log` file. This helps in debugging and tracking user interactions.

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Special thanks to the Python community for the excellent libraries used in this project
- Thanks to all contributors who helped improve this application
