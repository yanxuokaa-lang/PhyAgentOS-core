import os
import matplotlib.pyplot as plt
import numpy as np

# Ensure assets directory exists
os.makedirs("assets", exist_ok=True)

# Categories from peer benchmark (jabr/classifier-benchmark)
categories = [
    "Support Dept\n(Choice)",
    "Email Intent\n(Choice)",
    "Secret Leak\n(Noul)",
    "Urgency\n(Noul)",
    "Incident Sev.\n(Score)",
    "Sentiment\n(Score)",
    "Frustration\n(Score)",
    "Refund Elig.\n(Noul)",
    "Macro\nAverage",
]

von_scores = [100.0, 100.0, 100.0, 100.0, 88.9, 100.0, 88.9, 70.0, 93.5]
gliner_scores = [93.3, 90.0, 50.0, 100.0, 55.6, 88.9, 100.0, 50.0, 78.5]
jev_scores = [100.0, 100.0, 100.0, 100.0, 77.8, 100.0, 100.0, 100.0, 97.2]

x = np.arange(len(categories))
width = 0.26

# Set dark technical aesthetic
plt.style.use("dark_background")
fig, ax = plt.subplots(figsize=(13.5, 7.2), dpi=300)
fig.patch.set_facecolor("#0b0f17")
ax.set_facecolor("#0b0f17")

# Render bars
rects1 = ax.bar(
    x - width,
    von_scores,
    width,
    label="Von-1.0 (Option-Marker, Local)",
    color="#00e5ff",
    edgecolor="#00b4d8",
    linewidth=1.2,
    zorder=3,
)
rects2 = ax.bar(
    x,
    gliner_scores,
    width,
    label="GLiNER2 (fastino/gliner2-large-v1, Local)",
    color="#a855f7",
    edgecolor="#9333ea",
    linewidth=1.2,
    zorder=3,
)
rects3 = ax.bar(
    x + width,
    jev_scores,
    width,
    label="TypeSafe Jev (Cloud API)",
    color="#64748b",
    edgecolor="#475569",
    linewidth=1.2,
    zorder=3,
)

# Axis styling
ax.set_ylabel("Accuracy (%)", fontsize=12, fontweight="bold", color="#f1f5f9", labelpad=12)
ax.set_xticks(x)
ax.set_xticklabels(categories, fontsize=9.5, color="#cbd5e1", fontweight="500")
ax.set_ylim(30, 115)
ax.grid(axis="y", linestyle="--", alpha=0.15, color="#94a3b8", zorder=0)

# Place legend centered at the top OUTSIDE the plot area to guarantee zero bar overlap
legend = ax.legend(
    loc="lower center",
    bbox_to_anchor=(0.5, 1.01),
    ncol=3,
    frameon=True,
    facecolor="#1e293b",
    edgecolor="#334155",
    fontsize=10.5,
    labelcolor="#f8fafc",
)
legend.get_frame().set_linewidth(1.0)

# Title placed above the legend
fig.suptitle(
    "Decision Model Benchmark: Von-1.0 vs GLiNER2 vs TypeSafe Jev\n(Independent Peer Benchmark: jabr/classifier-benchmark)",
    fontsize=14,
    fontweight="bold",
    color="#ffffff",
    y=0.98,
)


# Value annotations
def annotate_bars(rects, text_color):
    for rect in rects:
        h = rect.get_height()
        ax.annotate(
            f"{h:.1f}%",
            xy=(rect.get_x() + rect.get_width() / 2, h),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=7.5,
            fontweight="bold",
            color=text_color,
        )


annotate_bars(rects1, "#00e5ff")
annotate_bars(rects2, "#c084fc")
annotate_bars(rects3, "#94a3b8")

plt.tight_layout(rect=[0, 0, 1, 0.93])
output_path = "assets/benchmark_comparison.png"
plt.savefig(output_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor="none")
print(f"Chart generated successfully: {output_path}")
