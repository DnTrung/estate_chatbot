import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import nltk
import re
import random
from datetime import datetime
import json
from langchain_community.llms import LlamaCpp
from openai import OpenAI
from user_context_db import UserContextDatabase


client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="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",  
)

class RealEstateChatbot:
    def __init__(self, property_data, document):
        self.properties = property_data
        self.document = document
        self.last_filtered_properties = pd.DataFrame()
        self.last_shown_index = 0
        self.db = UserContextDatabase()
        self.user_id = f"user_{random.randint(10000, 99999)}"

        # Fill NaN values to avoid issues
        self.properties = self.properties.fillna({
            'description': '',
            'Address': '',
            'Price': 0,
            'Area': 0,
            'Bedrooms': 0,
            'Bathrooms': 0,
            'House direction': 'Không có thông tin',
            'Balcony direction': 'Không có thông tin',
            'Legal status': 'Không có thông tin',
            'Furniture state': 'Không có thông tin'
        })
        
        self.conversation_history = []
        self.user_preferences = {
            'user_id': self.user_id,
            'min_price': None,
            'max_price': None,
            'min_area': None,
            'max_area': None,
            'bedrooms': None,
            'bathrooms': None,
            'locations': [],
            'house_direction': None,
            'furniture_state': None,
            'legal_state': None
        }
        self.staff_suggestions = None
        
        # Create combined text for better search
        self.properties['search_text'] = self.properties.apply(
            lambda row: self._create_search_text(row), axis=1
        )
        
        # Prepare vectorizer for text similarity
        self.vectorizer = TfidfVectorizer(
            analyzer='word',
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.95,
            stop_words=['và', 'có', 'là', 'với', 'tại', 'trong', 'của']
        )
        self.search_vectors = self.vectorizer.fit_transform(self.properties['search_text'])
        
        # Extract location data
        self.locations = set()
        for address in self.properties['Address']:
            parts = [p.strip() for p in str(address).split(',')]
            self.locations.update(parts)
        
    def _create_search_text(self, row):
        """Create a combined text representation for search purposes"""
        search_text = f"{row['Address']} {row['description']} {row['House direction']} {row['Balcony direction']} "
        search_text += f"{row['Legal status']} {row['Furniture state']} {row['Bedrooms']} phòng ngủ {row['Bathrooms']} phòng tắm "
        search_text += f"{row['Area']} m2 {row['Price']} tỷ"
        return search_text
                
    def normalize(self,locations):
        normalized_locations = []
        for text in locations:
            normalized_locations.append(
                text.lower()
                .replace("quận", "quận") # handle weird accents  
                .strip()
            )
        return normalized_locations

    def _filter_properties(self, df=None):
        """Filter properties based on user preferences"""
        if df is None:
            filtered = self.properties.copy()
        else:
            filtered = df.copy()

        # Filter by price
        if self.user_preferences['min_price'] is not None:
            filtered = filtered[filtered['Price'] >= self.user_preferences['min_price']]
        if self.user_preferences['max_price'] is not None:
            filtered = filtered[filtered['Price'] <= self.user_preferences['max_price']]
        
        # Filter by area
        if self.user_preferences['min_area'] is not None:
            filtered = filtered[filtered['Area'] >= self.user_preferences['min_area']]
        if self.user_preferences['max_area'] is not None:
            filtered = filtered[filtered['Area'] <= self.user_preferences['max_area']]
        
        # Filter by bedrooms
        if self.user_preferences['bedrooms'] is not None:
            filtered = filtered[filtered['Bedrooms'] >= self.user_preferences['bedrooms']]
        
        # Filter by bathrooms
        if self.user_preferences['bathrooms'] is not None:
            filtered = filtered[filtered['Bathrooms'] >= self.user_preferences['bathrooms']]
        
        # Filter by location (combine matches from all locations)
        if self.user_preferences['locations']:
            locations = self.user_preferences['locations']
            result_sets = []

            for loc in locations:
                normalized_query = self.normalize([loc])[0]

                # Find all rows where the normalized address contains the normalized query
                matches = filtered[filtered['Address'].apply(
                    lambda x: re.search(rf'\b{re.escape(normalized_query)}\b', self.normalize([x])[0]) is not None
                )]

                result_sets.append(matches)

            # Combine all matched rows (union) and remove duplicates
            if result_sets:
                combined_matches = pd.concat(result_sets).drop_duplicates()
                if combined_matches.empty:
                    # Fall back to vector search on full combined location string
                    location_query = ' '.join(locations)
                    query_vector = self.vectorizer.transform([location_query])
                    all_similarity_scores = cosine_similarity(query_vector, self.search_vectors).flatten()
                    filtered['similarity_score'] = all_similarity_scores[filtered.index]
                    location_threshold = 0.3  
                    filtered = filtered[filtered['similarity_score'] >= location_threshold]
                    filtered = filtered.sort_values('similarity_score', ascending=False)
                else:
                    filtered = combined_matches
        

        # Filter by direction
        if self.user_preferences['house_direction'] is not None:
            user_dir = self.user_preferences['house_direction'].strip().lower()

            def is_exact_direction(dir_value):
                # Normalize both user input and data by stripping, lowercasing, and removing hyphens/spaces
                dir_cleaned = str(dir_value).strip().lower().replace('-', '').replace(' ', '')
                user_cleaned = user_dir.replace('-', '').replace(' ', '')
                return dir_cleaned == user_cleaned

            direction_mask = filtered['House direction'].apply(is_exact_direction)
            filtered = filtered[direction_mask]


        
        # Filter by requirements using vector search
        if self.user_preferences['furniture_state']:
            filtered = filtered[filtered['Furniture state'].apply(
                lambda x: self.user_preferences['furniture_state'].lower() in str(x).lower()
            )]
        if self.user_preferences['legal_state']:
            filtered = filtered[filtered['Legal status'].apply(
                lambda x: self.user_preferences['legal_state'].lower() in str(x).lower()
            )]
    
        filtered = filtered.sample(frac=1).reset_index(drop=True)
        return filtered

    def process_message(self, user_message, staff_suggestion):
        """Process user message and generate response"""
        result = self._update_user_preferences(user_message)

        if staff_suggestion and user_message:
            user_message = user_message + " " + staff_suggestion
        elif user_message and not staff_suggestion:
            user_message = user_message
        else:
            user_message = staff_suggestion
        if isinstance(result, str):
            response = result  # This is a direct answer to a real estate question
        # Store the response
        elif any(value for key, value in self.user_preferences.items() if value):
            response = self.personalize(self._generate_response(user_message))
        else:
            response = "dã cập nhật thông tin của bạn. Bạn có thể hỏi tôi về bất động sản hoặc yêu cầu tìm kiếm căn hộ, nhà phố hoặc biệt thự"
        return response
    
    def process_to_AI(self, user_message, staff_suggestion):
        """Process user message and generate response"""
        if staff_suggestion and user_message:
            user_message = user_message + " " + staff_suggestion
        elif user_message and not staff_suggestion:
            user_message = user_message
        else:
            user_message = staff_suggestion

        # Store the message
        self.conversation_history.append({"role": "user", "message": user_message, "time": datetime.now()})

        # Extract user preferences or handle real estate questions
        result = self._update_user_preferences(user_message)
        
        if isinstance(result, str):
            response = result  # This is a direct answer to a real estate question
        # Store the response
        elif any(value for key, value in self.user_preferences.items() if value):
            response = self._generate_response(user_message)
        else:
            response = "dã cập nhật thông tin của bạn. Bạn có thể hỏi tôi về bất động sản hoặc yêu cầu tìm kiếm căn hộ, nhà phố hoặc biệt thự"
        self.conversation_history.append({"role": "bot", "message": response, "time": datetime.now()})
        print(self.user_preferences)
        return response
    
    def personalize(self, user_message, staff_suggestion=None):
        staff_suggestion = staff_suggestion if staff_suggestion else ""
        prompt = f"""
        This is user information:
        {self.db.get_user(self.user_id)}
        This is the system response, personalize to the user
        {self.process_to_AI(user_message, staff_suggestion)}
        This is the user message:
        {user_message}
        Keep the original meaning, but make it more personalized to the user.
        If user mentioned keyword: nữ, the response must be Chào chị.
        If user mentioned keyword: nam, the response must be Chào anh.
        Keep the response gentle and friendly.
        Return the response only, do not return JSON or any other format.

"""
        response = client.chat.completions.create(
            model="openai/gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "You are an AI assistant helping to personalize the response to the user."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.2,
        )
        output_text = response.choices[0].message.content.strip()
        return output_text

    def _update_user_preferences(self, message):
        prompt = f"""
        Current extracted preferences: {json.dumps(self.user_preferences, ensure_ascii=False)}
        Current user information: {json.dumps(getattr(self, 'user_information', {}), ensure_ascii=False)}
        This is the document written by staff, read it, analyze it and responding must follow the document:
        {self.document}

        1. Extracting and updating their real estate preferences and personal information
        2. Answering questions about real estate concepts in a clear, concise, and friendly way

        Please follow the logic below depending on the user's message:

        ---

        **Case 1: If the message is a real estate question**  
        (e.g., "mét vuông là gì", "lộ giới là gì", "sổ hồng là sao?", etc.)

        Respond with a short and clear explanation in Vietnamese.  
        Do **not** return JSON.  
        Keep it conversational and helpful.

        ---

        **Case 2: If the message provides user preferences or personal information**

        Extract the data and return it wrapped in this format:
        If user not mentioned any keyword in: tìm, nhà, căn hộ, biệt thự, đất, etc. Just return ONE JSON block about user information only.        
        <json>
        {{
            "user_preferences": {{
                "min_price": float or null (in **billion VND**),
                "max_price": float or null (in **billion VND**),
                "min_area": float or null (in m²),
                "max_area": float or null (in m²),
                "bedrooms": int or null,
                "bathrooms": int or null,
                "locations": list of strings,
                "house_direction": string or null,
                "legal_state": string or null, (if user mentioned "sổ đỏ", "sổ hồng", "sổ chung", "sổ riêng", etc. return Have Certificate)
                "furniture_state": string or null
            }},
            "user_information": {{
                "name": str or null,
                "age": int or null,
                "gender": str or null,
                "income_level": str or null,
                "budget": str or null,
                "owned_assets": str or null,
                "hobbies": str or null,
                "preferred_brands": str or null,
                "family_info": str or null,
            }}
        }}
        </json>

        ---

        If a user describes estimated travel time from a landmark (e.g. "cách quận Đống Đa khoảng 30 phút đi xe"), infer nearby districts or areas and populate the `locations` list accordingly.

        If user mentions family size (e.g., “2 vợ chồng và 2 con”), you may infer:
        - min_area, bedrooms, bathrooms based on this mapping:
            - 1–2 people: min_area = 30, bedrooms = 1, bathrooms = 1
            - 3–4 people: min_area = 50, bedrooms = 2, bathrooms = 1
            - 5–6 people: min_area = 70, bedrooms = 3, bathrooms = 3
            - >6 people: min_area = 90, bedrooms = 4, bathrooms = 4
        Below is the user message:
        "{message}"
"""


        response = client.chat.completions.create(
            model="openai/gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "You are an AI assistant helping to extract real estate preferences, user personal info and answering real estate questions."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.2,
        )
        output_text = response.choices[0].message.content.strip()
        print("Model response:", output_text)
    
        # Check if the response is a direct answer (not JSON)
        if not output_text.startswith("<json>"):
            return output_text  # This is a direct answer to a real estate question

        # Extract JSON inside <json>...</json> block
        json_match = re.search(r"<json>(.*?)</json>", output_text, re.DOTALL)
        if json_match:
            json_data = json_match.group(1).strip()
            try:
                parsed_data = json.loads(json_data)

                # Update user preferences
                preferences = parsed_data.get("user_preferences", {})
                for key, value in preferences.items():
                    if key == "locations" and isinstance(value, list):
                        if len(value) > 1:
                            for loc in value:
                                if loc not in self.user_preferences["locations"]:
                                    self.user_preferences["locations"].append(loc)
                        elif len(value) == 1:
                            self.user_preferences["locations"] = None
                            self.user_preferences["locations"] = [value[0]]
                    else:
                        self.user_preferences[key] = value

                # Update user information
                user_info = parsed_data.get("user_information", {})
                if not hasattr(self, "user_information"):
                    self.user_information = {}
                self.user_information.update(user_info)

                # Update database
                if hasattr(self, 'db') and hasattr(self, 'user_id'):
                    self.db.update_user(self.user_id, **self.user_information)

                return True  # Indicates user preferences were updated
            except json.JSONDecodeError as e:
                print("❌ Failed to parse JSON from model:", e)
                return False
        return False



        
    
    def _generate_response(self, user_message):
        """Generate response based on user message and preferences"""
        # Check if this is a greeting or general question
        greeting_keywords = ['xin chào', 'hello', 'hi', 'chào']
        help_keywords = ['giúp', 'tìm', 'muốn', 'cần', 'hỗ trợ','nhà','căn']
        
        # Process greetings
        if any(keyword in user_message.lower() for keyword in greeting_keywords) and len(self.conversation_history) <= 1:
            return "Xin chào! Tôi là trợ lý AI chuyên về bất động sản. Tôi có thể giúp bạn tìm kiếm căn hộ, nhà phố hoặc biệt thự theo nhu cầu của bạn. Bạn đang tìm kiếm bất động sản như thế nào? Hoặc bạn có thắc mắc nào cần giải đáp không?"
        
        if "thêm" in user_message.lower():
            additional_count = 3  # default
            match = re.search(r'thêm\s*(\d+)?', user_message.lower())
            if match and match.group(1):
                additional_count = int(match.group(1))
            
            if self.last_filtered_properties is not None and not self.last_filtered_properties.empty:
                start = self.last_shown_index
                end = start + additional_count
                addition_properties = self._filter_properties(self.last_filtered_properties)
                more_props = addition_properties.iloc[start:end]
                
                if more_props.empty:
                    self._update_user_preferences(user_message)
                    additional_properties = self._filter_properties()
                    more_props = additional_properties.iloc[start:end]

                response = f"Dưới đây là {len(more_props)} bất động sản khác phù hợp:\n\n"
                for i, (_, prop) in enumerate(more_props.iterrows(), start + 1):
                    if not prop['description'] or pd.isna(prop['description']):
                        description = f"Căn hộ tại {prop['Address']}, diện tích {prop['Area']}m², "
                        description += f"{prop['Bedrooms']} phòng ngủ, {prop['Bathrooms']} phòng tắm, "
                        description += f"hướng {prop['House direction']}, ban công hướng {prop['Balcony direction']}. "
                        description += f"Nội thất: {prop['Furniture state']}. Mức giá: {prop['Price']} tỷ VNĐ."
                    else:
                        description = prop['description']
                    response += f"{i}. {description}\n\n"
                
                self.last_shown_index = end
                response += "Bạn muốn xem thêm không, hay cần điều chỉnh tiêu chí tìm kiếm?"
                return response
            else:
                return "Hiện tại tôi chưa có gợi ý nào trước đó để tiếp tục. Bạn vui lòng nhập yêu cầu tìm kiếm trước nhé."

        # Process help requests or general search
        if any(keyword in user_message.lower() for keyword in help_keywords) and self.user_preferences['locations']:
            filtered_properties = self._filter_properties()
            
            if len(filtered_properties) == 0:
                return "Xin lỗi, tôi không tìm thấy bất động sản nào phù hợp với yêu cầu của bạn. Bạn có thể điều chỉnh các tiêu chí như giá, diện tích hoặc vị trí không?"
            
            # If we have staff suggestions, prioritize them
            if self.staff_suggestions:
                response = self.staff_suggestions + "\n\n"
            else:
                response = ""
            
            # Get top 3 properties
            top_properties = filtered_properties.head(3)
            self.last_filtered_properties = filtered_properties
            self.last_shown_index = 3
            
            response += f"Tôi đã tìm thấy {len(filtered_properties)} bất động sản phù hợp với yêu cầu của bạn. Dưới đây là một số gợi ý:\n\n"
            
            for i, (_, prop) in enumerate(top_properties.iterrows(), 1):
                if not prop['description'] or pd.isna(prop['description']):
                    description = f"Căn hộ tại {prop['Address']}"
                    
                    if not pd.isna(prop['Area']):
                        description += f", diện tích {prop['Area']}m²"
                    if not pd.isna(prop['Bedrooms']):
                        description += f", {int(prop['Bedrooms'])} phòng ngủ"
                    if not pd.isna(prop['Bathrooms']):
                        description += f", {int(prop['Bathrooms'])} phòng tắm"
                    if not pd.isna(prop['House direction']):
                        description += f", hướng {prop['House direction']}"
                    if not pd.isna(prop['Balcony direction']):
                        description += f", ban công hướng {prop['Balcony direction']}"
                    if not pd.isna(prop['Furniture state']):
                        description += f". Nội thất: {prop['Furniture state']}"
                    if not pd.isna(prop['Price']):
                        description += f". Mức giá: {prop['Price']} tỷ VNĐ"
                    
                    description += "."
                else:
                    description = prop['description']
                
                response += f"{i}. {description}\n\n"
            return response
        
        
        
        
        # Process feature inquiries
        feature_keywords = {
            'giá': 'Price', 
            'diện tích': 'Area', 
            'phòng ngủ': 'Bedrooms', 
            'phòng tắm': 'Bathrooms',
            'hướng': 'House direction',
            'pháp lý': 'Legal status',
            'nội thất': 'Furniture state'
        }
        
        for keyword, column in feature_keywords.items():
            if keyword in user_message.lower():
                filtered_properties = self._filter_properties()
                
                if len(filtered_properties) == 0:
                    return f"Xin lỗi, tôi không tìm thấy thông tin về {keyword} cho bất kỳ bất động sản nào phù hợp với yêu cầu của bạn."
                
                # Get statistics on the feature
                if column in ['Price', 'Area']:
                    min_val = filtered_properties[column].min()
                    max_val = filtered_properties[column].max()
                    avg_val = filtered_properties[column].mean()
                    
                    unit = "tỷ VNĐ" if column == 'Price' else "m²"
                    
                    response = ""
                    response += f"Dựa trên các tiêu chí của bạn, {keyword} dao động từ {min_val:.2f} đến {max_val:.2f} {unit}, "
                    response += f"với mức trung bình là {avg_val:.2f} {unit}.\n\n"
                    
                    if len(filtered_properties) > 0:
                        response += "Dưới đây là một số lựa chọn phù hợp:\n\n"
                        
                        for i, (_, prop) in enumerate(filtered_properties.head(3).iterrows(), 1):
                            if not prop['description'] or pd.isna(prop['description']):
                                description = f"Căn hộ tại {prop['Address']}, diện tích {prop['Area']}m², "
                                description += f"{prop['Bedrooms']} phòng ngủ, {prop['Bathrooms']} phòng tắm, "
                                description += f"hướng {prop['House direction']}. Mức giá: {prop['Price']} tỷ VNĐ."
                            else:
                                description = prop['description']
                            
                            response += f"{i}. {description}\n\n"
                    
                    return response
                else:
                    value_counts = filtered_properties[column].value_counts()
                    
                    response += f"Dựa trên các tiêu chí của bạn, phân bố {keyword} như sau:\n\n"
                    
                    for value, count in value_counts.items():
                        response += f"- {value}: {count} căn\n"
                    
                    response += "\nDưới đây là một số lựa chọn phù hợp:\n\n"
                    
                    for i, (_, prop) in enumerate(filtered_properties.head(3).iterrows(), 1):
                        if not prop['description'] or pd.isna(prop['description']):
                            description = f"Căn hộ tại {prop['Address']}, diện tích {prop['Area']}m², "
                            description += f"{prop['Bedrooms']} phòng ngủ, {prop['Bathrooms']} phòng tắm, "
                            description += f"hướng {prop['House direction']}. Mức giá: {prop['Price']} tỷ VNĐ."
                        else:
                            description = prop['description']
                        
                        response += f"{i}. {description}\n\n"
                    
                    return response
        
        # Search using vector search for general inquiries
        vectorized_query = self.vectorizer.transform([user_message])
        similarity_scores = cosine_similarity(vectorized_query, self.search_vectors).flatten()
        
        # Create a copy of properties with similarity scores
        scored_properties = self.properties.copy()
        scored_properties['similarity_score'] = similarity_scores
        
        # Filter properties with meaningful similarity
        search_threshold = 0.1  # Adjust as needed
        relevant_properties = scored_properties[scored_properties['similarity_score'] >= search_threshold]
        
        if len(relevant_properties) > 0:
            # Sort by similarity score
            relevant_properties = relevant_properties.sort_values('similarity_score', ascending=False)
            
            response = ""
            response += f"Dựa trên yêu cầu của bạn, tôi đã tìm thấy {len(relevant_properties)} bất động sản phù hợp. Đây là một số gợi ý hàng đầu:\n\n"
            
            for i, (_, prop) in enumerate(relevant_properties.head(3).iterrows(), 1):
                if not prop['description'] or pd.isna(prop['description']):
                    description = f"Căn hộ tại {prop['Address']}, diện tích {prop['Area']}m², "
                    description += f"{prop['Bedrooms']} phòng ngủ, {prop['Bathrooms']} phòng tắm, "
                    description += f"hướng {prop['House direction']}, ban công hướng {prop['Balcony direction']}. "
                    description += f"Nội thất: {prop['Furniture state']}. Mức giá: {prop['Price']} tỷ VNĐ."
                else:
                    description = prop['description']
                
                response += f"{i}. {description}\n\n"
            
            response += "Bạn có muốn biết thêm thông tin về bất kỳ căn hộ nào trong số này không?"
            
            return response
        
        # Default response if we can't categorize the query
        return "Xin lỗi, tôi không hiểu rõ yêu cầu của bạn. Bạn có thể cho tôi biết bạn đang tìm kiếm bất động sản như thế nào về giá cả, diện tích, vị trí hoặc các tiêu chí khác không?"

    def get_user_preferences(self):
        """Return current user preferences for debugging"""
        return self.user_preferences

    def reset_conversation(self):
        """Reset the conversation history and preferences"""
        self.conversation_history = []
        self.user_preferences = {
            'min_price': None,
            'max_price': None,
            'min_area': None,
            'max_area': None,
            'bedrooms': None,
            'bathrooms': None,
            'locations': [],
            'house_direction': None,
            'furniture_state': None,
            'legal_state': None
        }
        self.staff_suggestions = None
        