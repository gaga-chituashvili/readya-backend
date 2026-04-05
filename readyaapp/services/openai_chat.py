from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def chat_with_document(user_message: str, document_text: str, conversation_history: list = None):
    """
    Chat with AI about a document
    
    Args:
        user_message: რას ეუბნება მომხმარებელი
        document_text: PDF/DOCX-ის ტექსტი
        conversation_history: წინა საუბრის ისტორია
    
    Returns:
        AI-ს პასუხი
    """
    
    messages = []
    

    messages.append({
        "role": "system",
        "content": """შენ ხარ Readya-ს ჭკვიანი ასისტენტი. 
        შენი მიზანია დაეხმარო მომხმარებელს დოკუმენტების გაგებაში.
        უპასუხე ქართულად, მკაფიოდ და ზუსტად.
        თუ გჭირდება დოკუმენტის წაკითხვა, გამოიყენე მოცემული ტექსტი."""
    })
    
    
    if document_text:
        messages.append({
            "role": "system",
            "content": f"დოკუმენტის ტექსტი:\n\n{document_text[:6000]}"
        })
    
   
    if conversation_history:
        messages.extend(conversation_history)
    

    messages.append({
        "role": "user",
        "content": user_message
    })
    
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.7,
        max_tokens=1000
    )
    
    return response.choices[0].message.content