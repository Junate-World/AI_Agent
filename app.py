import os
import logging
import uuid
import json
from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
import re
from typing import Dict, Any, List

# Import our modules
from config import *
from llm.ollama_client import ollama_client
from llm.prompts import SYSTEM_PROMPT, RAG_PROMPT_TEMPLATE, CHAT_WITH_CONTEXT_TEMPLATE, WELCOME_MESSAGE, ERROR_MESSAGES
from rag.vector_store import vector_store
from memory.session_memory import session_manager
from tools.create_ticket import ticket_manager
from tools.order_status import order_manager

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
CORS(app)

def initialize_app():
    """Initialize application"""
    logger.info("Initializing AI Support Agent...")
    
    # Check Ollama connection
    if not ollama_client.check_connection():
        logger.warning("Could not connect to Ollama. Make sure Ollama is running.")
    else:
        logger.info("Connected to Ollama successfully")
    
    # Load or create vector store
    if not vector_store.load():
        logger.info("Building vector store from knowledge base...")
        vector_store.rebuild_from_directory()
    
    # Log stats
    stats = vector_store.get_stats()
    logger.info(f"Vector store loaded with {stats['total_documents']} documents")
    
    logger.info("AI Support Agent initialized successfully")

def generate_fallback_response(user_message: str, context: str = "") -> str:
    """Generate a fallback response when Ollama is not available"""
    user_message_lower = user_message.lower()
    
    # Check for common patterns
    if any(word in user_message_lower for word in ['hello', 'hi', 'hey', 'greetings']):
        return "Hello! I'm your AI support assistant. How can I help you today?"
    
    elif any(word in user_message_lower for word in ['help', 'what can you do', 'capabilities']):
        return """I can help you with:
        
📋 **Support Tasks:**
- Create support tickets
- Check order status
- Answer questions about products and services

📚 **Knowledge Base:**
I have access to documentation about our products, services, and support procedures.

💡 **Try asking:**
- "What products do you offer?"
- "Check order ORD-001"
- "Create a ticket for billing issue"
- "How do I reset my password?"

Note: I'm currently running in fallback mode. For full AI responses, please ensure Ollama is running properly."""
    
    elif any(word in user_message_lower for word in ['order', 'status', 'track']):
        if 'ord-' in user_message_lower:
            return "I can help check your order status! However, I need to connect to order system to get real-time information. Please try again when the AI service is fully available."
        else:
            return "To check your order status, please provide your order ID (e.g., ORD-001)."
    
    elif any(word in user_message_lower for word in ['ticket', 'support', 'issue', 'problem']):
        return "I can help create a support ticket for you! Please describe your issue and I'll create a ticket. However, I need the AI service to be fully available to process this properly."
    
    elif any(word in user_message_lower for word in ['product', 'service', 'offer']):
        return """Based on our knowledge base, we offer various products and services:

🖥️ **Products:**
- Laptops and desktops
- Smartphones and tablets
- Accessories and peripherals

🛠️ **Services:**
- Technical support
- Order tracking
- Billing assistance
- Account management

For specific details about any product or service, please ask when the AI service is fully available."""
    
    else:
        return f"""I understand you're asking about: "{user_message}"

However, I'm currently running in limited mode because the AI service (Ollama) is not responding properly. 

**What you can do:**
1. Try your question again in a few minutes
2. Check if Ollama is running: `ollama list`
3. Restart Ollama if needed: `ollama serve`

For urgent assistance, you can contact our support team directly at support@example.com or call 1-800-SUPPORT."""

def extract_tool_calls(response: str) -> List[Dict[str, Any]]:
    tool_calls = []
    
    # Simple pattern matching for tool calls
    patterns = [
        r'create_ticket\((.*?)\)',
        r'check_order_status\((.*?)\)',
        r'search_knowledge_base\((.*?)\)'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, response, re.DOTALL)
        for match in matches:
            tool_name = pattern.split('\\(')[0]
            try:
                # Parse arguments (simple approach)
                args = {}
                if match.strip():
                    # This is a simplified parser - in production you'd want something more robust
                    if 'description=' in match:
                        desc_match = re.search(r'description=["\']([^"\']+)["\']', match)
                        if desc_match:
                            args['description'] = desc_match.group(1)
                    
                    if 'priority=' in match:
                        priority_match = re.search(r'priority=["\']([^"\']+)["\']', match)
                        if priority_match:
                            args['priority'] = priority_match.group(1)
                    
                    if 'category=' in match:
                        category_match = re.search(r'category=["\']([^"\']+)["\']', match)
                        if category_match:
                            args['category'] = category_match.group(1)
                    
                    if 'order_id=' in match:
                        order_match = re.search(r'order_id=["\']([^"\']+)["\']', match)
                        if order_match:
                            args['order_id'] = order_match.group(1)
                    
                    if 'query=' in match:
                        query_match = re.search(r'query=["\']([^"\']+)["\']', match)
                        if query_match:
                            args['query'] = query_match.group(1)
                
                tool_calls.append({
                    'tool': tool_name,
                    'args': args
                })
            except Exception as e:
                logger.error(f"Error parsing tool call: {e}")
    
    return tool_calls

def execute_tool_call(tool_call: Dict[str, Any]) -> str:
    """Execute a tool call and return the result"""
    tool_name = tool_call['tool']
    args = tool_call['args']
    
    try:
        if tool_name == 'create_ticket':
            ticket = ticket_manager.create_ticket(
                description=args.get('description', 'No description provided'),
                priority=args.get('priority', 'medium'),
                category=args.get('category', 'general')
            )
            return f"✅ Created support ticket {ticket.ticket_id} with {ticket.priority} priority."
        
        elif tool_name == 'check_order_status':
            order_id = args.get('order_id')
            if not order_id:
                return "❌ Please provide an order ID."
            
            order = order_manager.get_order(order_id)
            if order:
                return order_manager.format_order_status(order)
            else:
                return f"❌ Order {order_id} not found. Please check the order ID and try again."
        
        elif tool_name == 'search_knowledge_base':
            query = args.get('query')
            if not query:
                return "❌ Please provide a search query."
            
            results = vector_store.search(query)
            if results:
                response = "📚 **Knowledge Base Results:**\n\n"
                for i, result in enumerate(results[:3], 1):
                    response += f"**{i}.** {result['text'][:200]}...\n"
                    response += f"*Source: {result['source']}*\n\n"
                return response
            else:
                return "📚 No relevant information found in the knowledge base."
        
        else:
            return f"❌ Unknown tool: {tool_name}"
    
    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {e}")
        return f"❌ Error executing {tool_name}: {str(e)}"

def generate_response(session_id: str, user_message: str) -> str:
    """Generate AI response with RAG and tools"""
    try:
        # Get session
        session_obj = session_manager.get_or_create_session(session_id)
        
        # Add user message to session
        session_obj.add_message('user', user_message)
        
        # Search knowledge base for relevant context
        context_docs = vector_store.search(user_message)
        context = ""
        if context_docs:
            context = "\n\n".join([doc['text'] for doc in context_docs])
        
        # Get conversation history
        recent_messages = session_obj.get_recent_messages(10)
        history = ""
        for msg in recent_messages[:-1]:  # Exclude current user message
            history += f"{msg.role}: {msg.content}\n"
        
        # Prepare prompt
        if context and history:
            prompt = CHAT_WITH_CONTEXT_TEMPLATE.format(
                history=history.strip(),
                context=context,
                message=user_message
            )
        elif context:
            prompt = RAG_PROMPT_TEMPLATE.format(
                context=context,
                question=user_message
            )
        else:
            prompt = user_message
        
        # Generate response
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = ollama_client.chat(messages, temperature=0.7)
        except Exception as e:
            logger.warning(f"Ollama failed, using fallback response: {e}")
            return generate_fallback_response(user_message, context)
        
        # Check for tool calls
        tool_calls = extract_tool_calls(response)
        if tool_calls:
            # Execute tool calls and append results
            tool_results = []
            for tool_call in tool_calls:
                result = execute_tool_call(tool_call)
                tool_results.append(result)
            
            if tool_results:
                # Generate final response with tool results
                tool_context = "\n\n".join(tool_results)
                final_prompt = f"{prompt}\n\nTool Results:\n{tool_context}\n\nPlease provide a helpful response based on these tool results."
                
                messages[-1]["content"] = final_prompt
                try:
                    response = ollama_client.chat(messages, temperature=0.7)
                except Exception as e:
                    logger.warning(f"Ollama failed on tool response, using fallback: {e}")
                    return generate_fallback_response(user_message, context)
        
        # Add assistant response to session
        session_obj.add_message('assistant', response)
        
        return response
    
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        return ERROR_MESSAGES.get("model_error", "I'm experiencing technical difficulties. Please try again.")

@app.route('/')
def index():
    """Main chat interface"""
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """Chat endpoint"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Get or create session ID
        session_id = session.get('session_id')
        if not session_id:
            session_id = str(uuid.uuid4())
            session['session_id'] = session_id
        
        # Generate response
        response = generate_response(session_id, user_message)
        
        return jsonify({
            'response': response,
            'session_id': session_id
        })
    
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        return jsonify({'error': ERROR_MESSAGES.get("model_error", "An error occurred")}), 500

@app.route('/api/status', methods=['GET'])
def status():
    """Get system status"""
    try:
        # Check Ollama connection
        ollama_connected = ollama_client.check_connection()
        
        # Get vector store stats
        vector_stats = vector_store.get_stats()
        
        # Get session stats
        session_stats = session_manager.get_session_stats()
        
        # Get ticket stats
        ticket_stats = ticket_manager.get_stats()
        
        # Get order stats
        order_stats = order_manager.get_stats()
        
        return jsonify({
            'status': 'healthy',
            'ollama_connected': ollama_connected,
            'vector_store': vector_stats,
            'sessions': session_stats,
            'tickets': ticket_stats,
            'orders': order_stats
        })
    
    except Exception as e:
        logger.error(f"Status endpoint error: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/rebuild-knowledge', methods=['POST'])
def rebuild_knowledge():
    """Rebuild knowledge base"""
    try:
        vector_store.rebuild_from_directory()
        stats = vector_store.get_stats()
        return jsonify({
            'message': 'Knowledge base rebuilt successfully',
            'stats': stats
        })
    
    except Exception as e:
        logger.error(f"Rebuild knowledge endpoint error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/models', methods=['GET'])
def list_models():
    """List available Ollama models"""
    try:
        models = ollama_client.list_models()
        return jsonify({'models': models})
    
    except Exception as e:
        logger.error(f"Models endpoint error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    initialize_app()
    app.run(host=HOST, port=PORT, debug=DEBUG)
