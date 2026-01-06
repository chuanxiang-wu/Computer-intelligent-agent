import os
import backoff
from openai import OpenAI, APIConnectionError, APIError, RateLimitError


class LLMEngineOpenAI:
    def __init__(
        self,
        base_url=None,
        api_key=None,
        model=None,
        rate_limit=-1,
        temperature=None,
        organization=None,
        **kwargs,
    ):
        assert model is not None, "model must be provided"
        self.model = model
        self.base_url = base_url
        self.api_key = api_key
        self.organization = organization
        self.request_interval = 0 if rate_limit == -1 else 60.0 / rate_limit
        self.llm_client = None
        self.temperature = temperature  # Can force temperature to be the same (in the case of o3 requiring temperature to be 1)

    # 重连接测试
    @backoff.on_exception(
        backoff.expo, (APIConnectionError, APIError, RateLimitError), max_time=60
    )

    def generate(self, messages, temperature=0.0, max_new_tokens=None, **kwargs):
        api_key = self.api_key or os.getenv("OPENAI_API_KEY")
        
        if api_key is None:
            raise ValueError(
                "An API Key needs to be provided in either the api_key parameter or as an environment variable named OPENAI_API_KEY"
            )
        organization = self.organization or os.getenv("OPENAI_ORG_ID")
        if not self.llm_client:
            if not self.base_url:
                self.llm_client = OpenAI(api_key=api_key, organization=organization)
            else:
                self.llm_client = OpenAI(base_url=self.base_url, api_key=api_key, organization=organization)
                
        return (
            self.llm_client.chat.completions.create(
                model=self.model,
                messages=messages,
                # max_completion_tokens=max_new_tokens if max_new_tokens else 4096,
                temperature=(temperature if self.temperature is None else self.temperature),
                **kwargs,
            )
            .choices[0]
            .message.content
        )

    def generate_with_thinking(self, messages, temperature=0.0, max_new_tokens=None, **kwargs):
        api_key = self.api_key or os.getenv("OPENAI_API_KEY")
        extra_body = {"thinking": {"type": "enabled"}}  # Enable thinking mode
        if api_key is None:
            raise ValueError(
                "An API Key needs to be provided in either the api_key parameter or as an environment variable named OPENAI_API_KEY"
            )
        organization = self.organization or os.getenv("OPENAI_ORG_ID")
        if not self.llm_client:
            if not self.base_url:
                self.llm_client = OpenAI(api_key=api_key, organization=organization)
            else:
                self.llm_client = OpenAI(base_url=self.base_url, api_key=api_key, organization=organization)
                
        completion = self.llm_client.chat.completions.create(
            model=self.model,
            messages=messages,
            # max_completion_tokens=max_new_tokens if max_new_tokens else 4096,
            temperature=(temperature if self.temperature is None else self.temperature),
            extra_body=extra_body,
            **kwargs,
        )
            
        thoughts = completion.choices[0].message.model_extra['reasoning_content']
        answer = completion.choices[0].message.content
        full_response = (
            f"<thoughts>\n{thoughts}\n</thoughts>\n\n<answer>\n{answer}\n</answer>\n"
        )
        return full_response
   
    

class LMMEnginevLLM:
    def __init__(
        self,
        base_url=None,
        api_key=None,
        model=None,
        rate_limit=-1,
        temperature=None,
        **kwargs,
    ):
        assert model is not None, "model must be provided"
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.request_interval = 0 if rate_limit == -1 else 60.0 / rate_limit
        self.llm_client = None
        self.temperature = temperature

    @backoff.on_exception(
        backoff.expo, (APIConnectionError, APIError, RateLimitError), max_time=60
    )

    def generate(
        self,
        messages,
        temperature=0.0,
        top_p=0.8,
        repetition_penalty=1.05,
        max_new_tokens=2048,
        **kwargs,
    ):
        api_key = self.api_key or os.getenv("vLLM_API_KEY")
        if api_key is None:
            raise ValueError(
                "A vLLM API key needs to be provided in either the api_key parameter or as an environment variable named vLLM_API_KEY"
            )
        base_url = self.base_url or os.getenv("vLLM_ENDPOINT_URL")
        if base_url is None:
            raise ValueError(
                "An endpoint URL needs to be provided in either the endpoint_url parameter or as an environment variable named vLLM_ENDPOINT_URL"
            )
        if not self.llm_client:
            self.llm_client = OpenAI(base_url=base_url, api_key=api_key)
        # Use self.temperature if set, otherwise use the temperature argument
        temp = self.temperature if self.temperature is not None else temperature
        completion = self.llm_client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_new_tokens if max_new_tokens else 4096,
            temperature=temp,
            top_p=top_p,
            extra_body={"repetition_penalty": repetition_penalty},
        )
        return completion.choices[0].message.content

    def generate_with_thinking(
        self,
        messages,
        temperature=0.0,
        top_p=0.8,
        repetition_penalty=1.05,
        max_new_tokens=2048,
        **kwargs,
    ):
        api_key = self.api_key or os.getenv("vLLM_API_KEY")
        extra_body = {"repetition_penalty": repetition_penalty, "thinking": {"type": "enabled"}}
        if api_key is None:
            raise ValueError(
                "A vLLM API key needs to be provided in either the api_key parameter or as an environment variable named vLLM_API_KEY"
            )
        base_url = self.base_url or os.getenv("vLLM_ENDPOINT_URL")
        if base_url is None:
            raise ValueError(
                "An endpoint URL needs to be provided in either the endpoint_url parameter or as an environment variable named vLLM_ENDPOINT_URL"
            )
        if not self.llm_client:
            self.llm_client = OpenAI(base_url=base_url, api_key=api_key)
        # Use self.temperature if set, otherwise use the temperature argument
        temp = self.temperature if self.temperature is not None else temperature
        completion = self.llm_client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_new_tokens if max_new_tokens else 4096,
            temperature=temp,
            top_p=top_p,
            extra_body=extra_body,
        )

        thoughts = completion.choices[0].message.model_extra['reasoning_content']
        answer = completion.choices[0].message.content
        full_response = (
            f"<thoughts>\n{thoughts}\n</thoughts>\n\n<answer>\n{answer}\n</answer>\n"
        )
        return full_response