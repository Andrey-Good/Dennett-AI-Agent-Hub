from huggingface_hub import hf_hub_download

repo_id = "dphn/Dolphin-X1-8B-GGUF"
filename = "Dolphin-X1-8B-Q3_K_L.gguf"
local_path = hf_hub_download(
    repo_id=repo_id,
    filename=filename,
    repo_type="model",
)
print("Saved to:", local_path)
