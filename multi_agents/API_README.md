# GPT Researcher API

This API allows you to integrate the GPT Researcher with n8n or any other workflow automation tool. It provides an endpoint that accepts research tasks and returns research results in JSON format.

## Setup

1. Install the required dependencies:
```bash
pip install -r api_requirements.txt
```

2. Start the API server:
```bash
python -m uvicorn multi_agents.api:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- Main API: http://localhost:8000
- Interactive Documentation: http://localhost:8000/docs
- OpenAPI Specification: http://localhost:8000/openapi.json

## API Endpoints

### GET /
Returns basic API information and links to documentation.

### POST /research
Creates a new research task and returns the research results.

#### Request Body

```json
{
  "query": "What are the latest trends in renewable energy?",
  "max_sections": 3,
  "publish_formats": {
    "markdown": true,
    "pdf": false,
    "docx": false
  },
  "include_human_feedback": false,
  "follow_guidelines": true,
  "model": "gpt-4",
  "guidelines": [
    "The report MUST be written in APA format",
    "Each sub section MUST include supporting sources using hyperlinks",
    "The report MUST be written in English"
  ],
  "verbose": true
}
```

#### Response

```json
{
  "status": "success",
  "data": {
    "report": {
      "title": "Latest Trends in Renewable Energy",
      "date": "2024-01-01",
      "introduction": "...",
      "table_of_contents": "...",
      "research_data": [...],
      "conclusion": "...",
      "sources": [...]
    }
  }
}
```

## Testing with cURL

You can test the API using cURL:

```bash
curl -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the latest trends in renewable energy?",
    "max_sections": 3,
    "publish_formats": {
      "markdown": true,
      "pdf": false,
      "docx": false
    },
    "include_human_feedback": false,
    "follow_guidelines": true,
    "model": "gpt-4",
    "guidelines": [
      "The report MUST be written in APA format",
      "Each sub section MUST include supporting sources using hyperlinks",
      "The report MUST be written in English"
    ],
    "verbose": true
  }'
```

## Integration with n8n

### Setting up the HTTP Request Node

1. Add an HTTP Request node in n8n
2. Configure the node:
   - Method: POST
   - URL: http://localhost:8000/research (or your server's address)
   - Headers:
     ```
     Content-Type: application/json
     ```
   - Body: Raw/JSON with your research task parameters

### Example n8n Workflow

1. **Trigger Node** (e.g., Webhook)
   - Receives the research query and parameters

2. **HTTP Request Node**
   - Method: POST
   - URL: http://localhost:8000/research
   - Body (example):
   ```json
   {
     "query": "{{$json.query}}",
     "max_sections": {{$json.max_sections || 3}},
     "publish_formats": {
       "markdown": true,
       "pdf": false,
       "docx": false
     }
   }
   ```

3. **Set Node** (optional)
   - Format the research results for your needs

4. **Output Node** (e.g., Email, Slack, etc.)
   - Send the formatted research results

### Important n8n Configuration Notes

1. Set appropriate timeout values in your HTTP Request node (recommended: 300 seconds or more)
2. Consider adding error handling nodes
3. The research process may take several minutes to complete

## Error Handling

The API returns appropriate HTTP status codes:
- 200: Success
- 500: Internal Server Error with error details

## Notes

- The API is asynchronous and may take some time to complete depending on the research task
- Make sure to handle timeouts appropriately in your n8n workflow
- The research results are returned in JSON format for easy integration with other systems
- You can access the interactive API documentation at http://localhost:8000/docs to test the API directly in your browser
