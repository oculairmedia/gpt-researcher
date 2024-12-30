import json5 as json
import json_repair
from langchain_community.adapters.openai import convert_openai_messages

from gpt_researcher.config.config import Config
from gpt_researcher.utils.llm import create_chat_completion

from loguru import logger


async def call_model(
    prompt: list,
    model: str,
    response_format: str = None,
):

    optional_params = {}
    if response_format == "json":
        optional_params = {"response_format": {"type": "json_object"}}

    cfg = Config()
    lc_messages = convert_openai_messages(prompt)

    try:
        response = await create_chat_completion(
            model=model,
            messages=lc_messages,
            temperature=0,
            llm_provider=cfg.smart_llm_provider,
            llm_kwargs=cfg.llm_kwargs,
            # cost_callback=cost_callback,
        )

        if response_format == "json":
            try:
                # Remove any JSON markdown formatting
                cleaned_json_string = response.strip("```json\n").strip("```")
                
                # Validate JSON structure
                if not cleaned_json_string.strip().startswith("{"):
                    raise ValueError("Response is not a valid JSON object")
                    
                # Attempt to parse JSON
                parsed = json.loads(cleaned_json_string)
                
                # Validate parsed JSON contains required fields
                if not isinstance(parsed, dict):
                    raise ValueError("Parsed JSON is not an object")
                    
                return parsed
                
            except Exception as e:
                print("⚠️ Error in reading JSON, attempting to repair JSON")
                logger.error(
                    f"Error in reading JSON, attempting to repair response: {response}"
                )
                try:
                    # Attempt to repair JSON
                    repaired = json_repair.loads(response)
                    if not isinstance(repaired, dict):
                        raise ValueError("Repaired JSON is not an object")
                    return repaired
                except Exception as repair_error:
                    logger.error(f"Failed to repair JSON: {repair_error}")
                    # Return empty JSON object as fallback
                    return {}
        else:
            return response

    except Exception as e:
        print("⚠️ Error in calling model")
        logger.error(f"Error in calling model: {e}")
        # Return empty JSON object as fallback
        return {}
