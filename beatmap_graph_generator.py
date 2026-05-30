import matplotlib.pyplot as plt
import numpy as np

def generate_graph(times, values, labels, output_file, title="", graph_title="Replay Graph", value_label="Star Rating", min_value=None, max_value=None, value_interval=0.5,
                   greens=[], blues=[], misses=[], finisher_misses=[], footer_title="Replay Stats", footer_text="", note=""):
    time_interval = 30 if times[-1] > 180 else 10
    if not max_value:
        highest_value = max([item for sublist in values for item in sublist])
        max_value = highest_value // value_interval * value_interval + value_interval
    
    plt.figure(figsize=(8, 4))
    plt.suptitle(title, wrap=True)
    if footer_text:
        graph = plt.subplot2grid((1, 3), (0, 0), colspan=2)
        footer = plt.subplot2grid((1, 3), (0, 2))
    else:
        graph = plt.subplot2grid((1, 3), (0, 0), colspan=3)
    
    for green in greens:
        graph.axvline(x=green, color="green", lw=1)
    for blue in blues:
        graph.axvline(x=blue, color="blue", lw=1)
    for finisher_miss in finisher_misses:
        graph.axvline(x=finisher_miss, color="purple", lw=1)
    for miss in misses:
        graph.axvline(x=miss, color="red", lw=1)
    for i in range(len(values)):
        if values[i] and labels[i]:
            graph.plot(times, values[i], label=labels[i])
    graph.set_title(graph_title)
    graph.set_xlabel("Seconds")
    graph.set_ylabel(value_label)
    if len(labels) > 1:
        graph.legend()
    graph.set_xticks(np.arange(0, times[-1] + time_interval, time_interval))
    graph.set_yticks(np.arange(0, max_value + value_interval, value_interval))
    graph.set_ylim(min_value if min_value else 0, max_value)
    graph.tick_params(axis="x", which="both", labelrotation=60)
    
    if footer_text:
        footer.set_title(footer_title)
        footer.tick_params(axis="both", which="both", bottom=False, labelbottom=False, left=False, labelleft=False)
        footer.text(0.01, 0.99, footer_text, verticalalignment="top", fontsize=8)
        if note:
            footer.text(0.01, 0.01, note, fontsize=8)
    
    plt.tight_layout(pad=1.5)
    plt.savefig(output_file)