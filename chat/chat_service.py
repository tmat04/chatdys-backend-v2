import openai
from typing import Dict, Any, List, Optional
from config.settings import settings
import asyncio
import json
import re

class ChatService:
    def __init__(self):
        # Initialize OpenAI client
        if settings.OPENAI_API_KEY:
            openai.api_key = settings.OPENAI_API_KEY
        else:
            print("⚠️  Warning: OPENAI_API_KEY not set")
        
        self.model = "gpt-4"
        self.max_tokens = 1000
        self.temperature = 0.7
        
        # System prompt for ChatDys
        self.system_prompt = """You are ChatDys, an AI assistant specialized in dysautonomia, POTS (Postural Orthostatic Tachycardia Syndrome), and Long Covid. You provide evidence-based medical information to help users understand their conditions and manage their symptoms.

Key guidelines:
1. Always provide accurate, evidence-based medical information
2. Cite sources when possible and mention if information comes from medical literature
3. Remind users that you're not a replacement for professional medical advice
4. Be empathetic and understanding of the challenges these conditions present
5. Focus on practical, actionable advice for symptom management
6. Explain medical terms in accessible language
7. Encourage users to work with their healthcare providers

Areas of expertise:
- POTS and other forms of dysautonomia
- Long Covid and post-viral syndromes
- Symptom management strategies
- Lifestyle modifications (diet, exercise, sleep)
- Treatment options and medications
- Diagnostic processes and tests

Always be supportive and acknowledge the real challenges these conditions present while providing helpful, accurate information."""

    async def get_response(
        self, 
        question: str, 
        user_id: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """Get AI response for user question"""
        
        try:
            # Prepare messages for OpenAI
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # Add conversation history if available
            if conversation_history:
                # Add last few messages for context (limit to avoid token limits)
                recent_history = conversation_history[-6:]  # Last 6 messages
                messages.extend(recent_history)
            
            # Add current question
            messages.append({"role": "user", "content": question})
            
            # Make OpenAI API call
            if settings.OPENAI_API_KEY:
                response = await self._call_openai(messages)
            else:
                # Fallback response when API key is not available
                response = await self._get_fallback_response(question)
            
            return response
            
        except Exception as e:
            print(f"❌ Chat service error: {str(e)}")
            return {
                "answer": "I apologize, but I'm experiencing technical difficulties right now. Please try again in a moment.",
                "error": str(e),
                "confidence_score": 0
            }

    async def _call_openai(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Make actual OpenAI API call"""
        try:
            response = await asyncio.to_thread(
                openai.ChatCompletion.create,
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                presence_penalty=0.1,
                frequency_penalty=0.1
            )
            
            answer = response.choices[0].message.content.strip()
            
            # Extract sources if mentioned in the response
            sources = self._extract_sources(answer)
            
            # Calculate confidence score based on response characteristics
            confidence_score = self._calculate_confidence(answer)
            
            return {
                "answer": answer,
                "sources": sources,
                "confidence_score": confidence_score,
                "model_used": self.model,
                "tokens_used": response.usage.total_tokens
            }
            
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")

    async def _get_fallback_response(self, question: str) -> Dict[str, Any]:
        """Provide fallback response when OpenAI is not available"""
        
        # Simple keyword-based responses for common topics
        question_lower = question.lower()
        
        if any(word in question_lower for word in ["pots", "postural", "tachycardia"]):
            answer = """POTS (Postural Orthostatic Tachycardia Syndrome) is a form of dysautonomia characterized by an abnormal increase in heart rate when standing up. Common symptoms include:

• Rapid heart rate (increase of 30+ bpm when standing)
• Dizziness or lightheadedness
• Fatigue
• Brain fog
• Nausea
• Chest pain

Management strategies often include:
• Increasing fluid and salt intake
• Wearing compression garments
• Gradual exercise programs
• Medications as prescribed by your doctor

Please consult with a healthcare provider familiar with POTS for proper diagnosis and treatment planning."""

        elif any(word in question_lower for word in ["long covid", "post covid", "covid"]):
            answer = """Long Covid refers to symptoms that persist for weeks or months after the acute phase of COVID-19. It can affect multiple body systems and may include:

• Fatigue and post-exertional malaise
• Brain fog and cognitive issues
• Shortness of breath
• Heart palpitations
• Sleep disturbances
• Autonomic dysfunction

Many Long Covid patients develop POTS or other forms of dysautonomia. Management is typically symptom-focused and may include:
• Pacing activities to avoid overexertion
• Gradual rehabilitation programs
• Symptom-specific treatments
• Support from specialized Long Covid clinics

Work with healthcare providers experienced in post-viral conditions for the best care approach."""

        elif any(word in question_lower for word in ["dysautonomia", "autonomic"]):
            answer = """Dysautonomia refers to disorders of the autonomic nervous system, which controls involuntary body functions like heart rate, blood pressure, and digestion. Types include:

• POTS (Postural Orthostatic Tachycardia Syndrome)
• Neurocardiogenic syncope
• Multiple system atrophy
• Pure autonomic failure

Common symptoms across types:
• Heart rate and blood pressure irregularities
• Temperature regulation issues
• Digestive problems
• Sleep disturbances
• Exercise intolerance

Treatment is typically individualized and may include lifestyle modifications, medications, and physical therapy. Specialist care from a neurologist or cardiologist familiar with autonomic disorders is recommended."""

        else:
            answer = """I'm currently experiencing technical difficulties with my AI processing system. However, I'm designed to help with questions about:

• POTS and dysautonomia
• Long Covid and post-viral syndromes
• Symptom management strategies
• Treatment options and lifestyle modifications

For immediate help, consider:
• Consulting with your healthcare provider
• Visiting reputable medical websites like Mayo Clinic or Cleveland Clinic
• Contacting patient advocacy organizations like Dysautonomia International

Please try your question again in a few moments when my systems are fully operational."""

        return {
            "answer": answer,
            "sources": [],
            "confidence_score": 60,  # Lower confidence for fallback responses
            "model_used": "fallback"
        }

    def _extract_sources(self, answer: str) -> List[Dict[str, str]]:
        """Extract potential sources mentioned in the response"""
        sources = []
        
        # Look for common medical source patterns
        source_patterns = [
            r"according to (.+?)(?:\.|,|$)",
            r"research shows (.+?)(?:\.|,|$)",
            r"studies indicate (.+?)(?:\.|,|$)",
            r"(.+?) guidelines",
            r"(.+?) research"
        ]
        
        for pattern in source_patterns:
            matches = re.findall(pattern, answer, re.IGNORECASE)
            for match in matches:
                if len(match.strip()) > 5:  # Avoid very short matches
                    sources.append({
                        "title": match.strip(),
                        "type": "reference"
                    })
        
        # Add some common reliable sources for dysautonomia/POTS
        if any(term in answer.lower() for term in ["pots", "dysautonomia", "long covid"]):
            sources.extend([
                {
                    "title": "Dysautonomia International",
                    "url": "https://www.dysautonomiainternational.org",
                    "type": "organization"
                },
                {
                    "title": "Mayo Clinic - POTS",
                    "url": "https://www.mayoclinic.org/diseases-conditions/postural-orthostatic-tachycardia-syndrome/symptoms-causes/syc-20361512",
                    "type": "medical_reference"
                }
            ])
        
        return sources[:3]  # Limit to 3 sources

    def _calculate_confidence(self, answer: str) -> int:
        """Calculate confidence score based on response characteristics"""
        confidence = 80  # Base confidence
        
        # Increase confidence for longer, detailed responses
        if len(answer) > 500:
            confidence += 10
        elif len(answer) < 100:
            confidence -= 20
        
        # Increase confidence if medical terms are used appropriately
        medical_terms = ["syndrome", "symptoms", "treatment", "diagnosis", "medication", "therapy"]
        term_count = sum(1 for term in medical_terms if term in answer.lower())
        confidence += min(term_count * 2, 10)
        
        # Decrease confidence if response seems uncertain
        uncertainty_phrases = ["i'm not sure", "might be", "possibly", "unclear"]
        uncertainty_count = sum(1 for phrase in uncertainty_phrases if phrase in answer.lower())
        confidence -= uncertainty_count * 5
        
        # Ensure confidence is within valid range
        return max(10, min(95, confidence))
