from unittest.mock import patch, MagicMock
import torch
from study_bites.utils import ml
from io import BytesIO
from PIL import Image

# Sample image
SAMPLE_IMAGE_BYTES = BytesIO()
Image.new("RGB", (64, 64), color="red").save(SAMPLE_IMAGE_BYTES, format="PNG")
SAMPLE_IMAGE_BYTES.seek(0)

@patch("study_bites.utils.ml.initialize_model")
@patch("study_bites.utils.ml.requests.get")
@patch("study_bites.utils.ml.model", new_callable=MagicMock)
@patch("study_bites.utils.ml.tokenizer", new_callable=MagicMock)
@patch("study_bites.utils.ml.image_processor", new_callable=MagicMock)
def test_classify_image_mocked(mock_image_processor, mock_tokenizer, mock_model, mock_requests_get, mock_initialize_model):
    # Mock initialize_model
    mock_initialize_model.return_value = None

    # Mock requests.get
    mock_response = MagicMock()
    mock_response.content = SAMPLE_IMAGE_BYTES.getvalue()
    mock_response.raise_for_status = MagicMock()
    mock_requests_get.return_value = mock_response

    # Correct way to mock tokenizer / image_processor
    # Create a mock object that has a `.to()` method
    mock_text_inputs = MagicMock()
    mock_text_inputs.to.return_value = {"input_ids": torch.tensor([[0]])}
    mock_tokenizer.return_value = mock_text_inputs

    mock_image_inputs = MagicMock()
    mock_image_inputs.to.return_value = {"pixel_values": torch.tensor([[[[0.0]]]])}
    mock_image_processor.return_value = mock_image_inputs
    
    # Mock model __call__ to return a fake output
    mock_output = MagicMock()
    mock_output.logits_per_image = torch.tensor([[10.0, 1.0, 1.0, 1.0, 1.0]])
    mock_model.return_value = mock_output
    
    # Run the function
    result = ml.classify_image("http://fake-url.com/image.png")
    
    # Since top label is not "chef" and prob > 0.75, should return True
    assert result is True

def test_classify_image_invalid_url():
    # Pass None or empty URL
    result = ml.classify_image(None)
    assert result is False
    
    result = ml.classify_image("")
    assert result is False