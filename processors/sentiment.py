# processors/sentiment.py

import torch
import torch.nn as nn
from transformers import RobertaModel, RobertaTokenizer

# --- This code is now correct and matches your model's structure ---
class Attention(nn.Module):
    def __init__(self, feature_dim, step_dim, bias=False, **kwargs):
        super(Attention, self).__init__(**kwargs)
        self.attention = nn.Linear(feature_dim, 1, bias=bias)

    def forward(self, x, mask=None):
        eij = self.attention(x)
        a = torch.exp(eij)
        if mask is not None:
            a = a * mask.unsqueeze(-1)
        a = a / (torch.sum(a, dim=1, keepdim=True) + 1e-10)
        weighted_input = x * a
        return torch.sum(weighted_input, dim=1)

class RobertaHAN(nn.Module):
    def __init__(self, roberta_model_name='roberta-base', num_classes=5): # FIX #1: Changed to 5 classes
        super(RobertaHAN, self).__init__()
        self.roberta = RobertaModel.from_pretrained(roberta_model_name)
        GRU_HIDDEN_SIZE = 128
        self.gru = nn.GRU(
            self.roberta.config.hidden_size,
            GRU_HIDDEN_SIZE,
            bidirectional=True,
            batch_first=True
        )
        self.sent_attn = Attention(GRU_HIDDEN_SIZE * 2, self.roberta.config.max_position_embeddings)
        self.classifier = nn.Sequential(
            nn.Identity(),
            nn.Linear(GRU_HIDDEN_SIZE * 2, num_classes)
        )

    def forward(self, input_ids, attention_mask):
        outputs = self.roberta(input_ids=input_ids, attention_mask=attention_mask)
        sequence_output = outputs.last_hidden_state
        gru_output, _ = self.gru(sequence_output)
        attn_output = self.sent_attn(gru_output, mask=attention_mask)
        logits = self.classifier(attn_output)
        return logits
# --------------------------------------------------------------------

class SentimentModel:
    def __init__(self, model_path='best_model.pth'):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = RobertaTokenizer.from_pretrained('roberta-base')
        
        # Instantiate the model with 5 classes
        self.model = RobertaHAN(num_classes=5)
        
        state_dict = torch.load(model_path, map_location=self.device)
        self.model.load_state_dict(state_dict)
        self.model.to(self.device)
        self.model.eval()

    def predict(self, text):
        inputs = self.tokenizer(text, return_tensors='pt', truncation=True, padding=True, max_length=512).to(self.device)
        with torch.no_grad():
            logits = self.model(input_ids=inputs['input_ids'], attention_mask=inputs['attention_mask'])
        
        predicted_class_id = torch.argmax(logits, dim=1).item()
        
        # FIX #2: Map the 5 output classes to 3 sentiment categories
        if predicted_class_id in [0, 1]:
            return 'negative'
        elif predicted_class_id == 2:
            return 'neutral'
        else: # Covers classes 3 and 4
            return 'positive'