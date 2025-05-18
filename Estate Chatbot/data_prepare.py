import logging
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("chatbot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_data():
        """Load and prepare property data"""
        try:
            property_data = pd.read_csv("data/vietnam_housing_dataset.csv")
            
            # Generate descriptions
            def generate_description(row):
                return (
                    f"Căn hộ tại {row['Address']}, diện tích {row['Area']}m², "
                    f"{row['Bedrooms']} phòng ngủ, {row['Bathrooms']} phòng tắm, "
                    f"hướng {row['House direction']}, ban công hướng {row['Balcony direction']}. "
                    f"Nội thất: {row['Furniture state']}. "
                    f"Pháp lý: {row['Legal status']}. "
                    f"Mức giá: {row['Price']} tỷ VNĐ."
                )
            
            property_data["description"] = property_data.apply(generate_description, axis=1)
            
            # Clean data
            property_data = property_data.fillna({
                'Bedrooms': 0, 
                'Bathrooms': 0,
                'House direction': 'Không xác định',
                'Balcony direction': 'Không xác định',
                'Furniture state': 'Không xác định',
                'Legal status': 'Không xác định'
            })
            
            logger.info(f"Loaded {len(property_data)} properties")
        
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            property_data = pd.DataFrame()  # Empty dataframe as fallback
        return property_data