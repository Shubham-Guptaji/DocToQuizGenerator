"""Generates a clean, valid 3-page educational PDF on Machine Learning using standard PDF streams."""
import os
from pathlib import Path


def create_minimal_pdf(output_path: Path):
    """
    Generate a valid 3-page educational PDF without requiring C-extensions.
    Each page contains well-formatted chapter text.
    """
    pages_content = [
        # Page 1
        (
            "AI & MACHINE LEARNING PRIMER: FOUNDATIONS\n\n"
            "Chapter 1: Supervised vs Unsupervised Learning\n\n"
            "Machine learning systems fall into three primary algorithmic paradigms:\n"
            "1. Supervised Learning: Models infer a function from labeled training data containing\n"
            "   input vectors X and target labels Y. Key applications include binary classification\n"
            "   (e.g., medical diagnostics) and continuous regression (e.g., house price forecasting).\n"
            "2. Unsupervised Learning: Discovers latent patterns, cluster boundaries, or low-dimensional\n"
            "   representations in unlabeled data. Notable algorithms include K-Means clustering,\n"
            "   Principal Component Analysis (PCA), and autoencoders.\n"
            "3. Reinforcement Learning: Agents optimize decision policies through environmental\n"
            "   rewards and penalties within a Markov Decision Process (MDP) setting."
        ),
        # Page 2
        (
            "ARTIFICIAL NEURAL NETWORKS & BACKPROPAGATION\n\n"
            "Chapter 2: Deep Architectures, Activation Functions, and Optimization\n\n"
            "Artificial neural networks consist of stacked layers of parameterized units:\n"
            "- Rectified Linear Unit (ReLU): Defined as f(x) = max(0, x). Solves vanishing gradient\n"
            "  problems across deep architectures and offers high computational efficiency.\n"
            "- Sigmoid: Squashes input to the range (0, 1), standard for binary classification heads.\n"
            "- Softmax: Normalizes real-valued logits into a categorical probability distribution\n"
            "  summing to 1.0, essential for multi-class classification.\n\n"
            "Backpropagation computes the exact analytical gradients of the loss function with\n"
            "respect to network weights by recursively applying the chain rule from the final layer\n"
            "backwards to input layers."
        ),
        # Page 3
        (
            "GENERALIZATION, OVERFITTING & REGULARIZATION\n\n"
            "Chapter 3: Mitigating Variance and Improving Generalization\n\n"
            "Overfitting occurs when a high-capacity model fits random noise in the training set,\n"
            "producing poor validation accuracy. Established regularization strategies include:\n"
            "1. L1 Regularization (Lasso): Adds the absolute sum of weights to loss, enforcing\n"
            "   parameter sparsity and serving as implicit feature selection.\n"
            "2. L2 Regularization (Ridge / Weight Decay): Penalizes squared weights, ensuring\n"
            "   smooth parameter distributions without extreme weight magnitudes.\n"
            "3. Dropout: Randomly zeros out hidden unit activations during forward training passes\n"
            "   with probability p, breaking co-adaptation between feature detectors.\n"
            "4. Early Stopping: Monitors validation error and terminates training when loss\n"
            "   consistently increases, preventing over-training."
        ),
    ]

    objects = []
    # 1: Catalog
    # 2: Outlines
    # 3: Pages
    # 4, 5, 6: Page objects
    # 7: Font object
    # 8, 9, 10: Content streams

    num_pages = len(pages_content)

    def escape_pdf_text(text: str) -> str:
        return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    # Build content streams
    stream_objs = []
    for content in pages_content:
        lines = content.split("\n")
        stream_lines = ["BT", "/F1 12 Tf", "50 740 Td", "16 TL"]
        first = True
        for line in lines:
            safe = escape_pdf_text(line)
            if first:
                stream_lines.append(f"({safe}) Tj")
                first = False
            else:
                stream_lines.append(f"T* ({safe}) Tj")
        stream_lines.append("ET")
        stream_data = "\n".join(stream_lines).encode("latin-1")
        stream_objs.append(stream_data)

    # Object IDs
    catalog_id = 1
    outlines_id = 2
    pages_id = 3
    page_ids = [4 + i for i in range(num_pages)]
    font_id = 4 + num_pages
    stream_ids = [font_id + 1 + i for i in range(num_pages)]

    obj_dict = {}

    obj_dict[catalog_id] = f"<< /Type /Catalog /Pages {pages_id} 0 R >>"
    obj_dict[outlines_id] = "<< /Type /Outlines /Count 0 >>"

    kids_str = " ".join([f"{pid} 0 R" for pid in page_ids])
    obj_dict[pages_id] = f"<< /Type /Pages /Kids [{kids_str}] /Count {num_pages} >>"

    for i in range(num_pages):
        pid = page_ids[i]
        sid = stream_ids[i]
        obj_dict[pid] = (
            f"<< /Type /Page /Parent {pages_id} 0 R "
            f"/MediaBox [0 0 612 792] "
            f"/Contents {sid} 0 R "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> >>"
        )

    obj_dict[font_id] = "<< /Type /Font /Subtype /Type1 /Name /F1 /BaseFont /Helvetica >>"

    for i in range(num_pages):
        sid = stream_ids[i]
        s_data = stream_objs[i]
        obj_dict[sid] = (
            f"<< /Length {len(s_data)} >>\nstream\n{s_data.decode('latin-1')}\nendstream"
        )

    # Assemble PDF with cross-reference table
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(b"%PDF-1.4\n")
        xref_offsets = {}
        for oid in sorted(obj_dict.keys()):
            xref_offsets[oid] = f.tell()
            f.write(f"{oid} 0 obj\n{obj_dict[oid]}\nendobj\n".encode("latin-1"))

        xref_pos = f.tell()
        total_objs = max(obj_dict.keys()) + 1
        f.write(f"xref\n0 {total_objs}\n".encode("latin-1"))
        f.write(b"0000000000 65535 f \n")
        for oid in range(1, total_objs):
            offset = xref_offsets.get(oid, 0)
            f.write(f"{offset:010d} 00000 n \n".encode("latin-1"))

        f.write(
            f"trailer\n<< /Size {total_objs} /Root {catalog_id} 0 R >>\n"
            f"startxref\n{xref_pos}\n%%EOF\n".encode("latin-1")
        )

    print(f"Generated PDF: {output_path} ({os.path.getsize(output_path)} bytes)")


if __name__ == "__main__":
    out = Path("sample_docs/machine_learning_primer.pdf")
    create_minimal_pdf(out)
