from huggingface_hub import hf_hub_download

repo_id = "unsloth/gemma-3-270m-it-qat-GGUF"
filename = "gemma-3-270m-it-qat-IQ4_NL.gguf"
local_path = hf_hub_download(
    repo_id=repo_id,
    filename=filename,
    repo_type="model",
)
print("Saved to:", local_path)
