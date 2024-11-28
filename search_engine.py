import os
import re
import time
import json
import string
from underthesea import text_normalize, word_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer
from PIL import Image
import streamlit as st

stopwords = None
punctuations = None
index = None


def init():
    global stopwords, punctuations, index

    print("Initializing")

    print("Loading stopwords")
    with open("vietnamese_stopwords.txt", "r", encoding="utf-8") as f:
        stopwords = set(f.read().split("\n"))

    print("Loading punctuations")
    punctuations = set(string.punctuation)

    print("Loading index")
    if not os.path.exists("index.json"):
        print("Index not found, creating index")
        ids = []
        texts = []
        for file in os.listdir("data"):
            ids.append(file[:-5])
            with open(os.path.join("data", file), "r", encoding="utf-8") as f:
                data = json.load(f)
                texts.append(data["content"])

        index = create_index(texts, ids)

        with open("index.json", "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=4)
    else:
        with open("index.json", "r", encoding="utf-8") as f:
            index = json.load(f)

    print("Done")


def preprocess_text(text):
    # normalize text
    text = text_normalize(text)
    # remove emoji
    text = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002500-\U00002BEF"
        "\U00002702-\U000027B0"
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001f926-\U0001f937"
        "\U00010000-\U0010ffff"
        "\u2640-\u2642"
        "\u2600-\u2B55"
        "\u200d"
        "\u23cf"
        "\u23e9"
        "\u231a"
        "\ufe0f"
        "\u3030"
        "]+",
        flags=re.UNICODE,
    ).sub(r"", text)
    # remove link
    text = re.compile(
        "https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&\/\/=]*)"
    ).sub(r"", text)
    # remove punctuation
    text = "".join([char for char in text if char not in punctuations])
    # tokenize
    tokens = word_tokenize(text)
    # make lower case
    tokens = [token.lower() for token in tokens]
    # remove stop words
    tokens = [token for token in tokens if token not in stopwords]

    return ["_".join(token.split()) for token in tokens]


def create_index(texts, ids=None):
    preprocessed_texts = [preprocess_text(text) for text in texts]

    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(
        " ".join(text) for text in preprocessed_texts
    )

    index = {"terms": vectorizer.get_feature_names_out().tolist(), "documents": []}
    for id, row in enumerate(tfidf_matrix.toarray()):
        term_scores = {
            term: float(score) for term, score in zip(index["terms"], row) if score > 0
        }
        index["documents"].append(
            {"id": id if ids is None else ids[id], "scores": term_scores}
        )

    return index


def search_by_cosine_similarity(query):
    query = preprocess_text(query)

    query_vector = [0] * len(index["terms"])
    for term in query:
        if term in index["terms"]:
            query_vector[index["terms"].index(term)] = 1

    query_magnitude = sum(a**2 for a in query_vector) ** 0.5
    if query_magnitude == 0:
        return []

    results = []
    for document in index["documents"]:
        document_vector = [document["scores"].get(term, 0) for term in index["terms"]]
        document_magnitude = sum(b**2 for b in document_vector) ** 0.5
        if document_magnitude == 0:
            continue
        similarity = sum(a * b for a, b in zip(query_vector, document_vector)) / (
            query_magnitude * document_magnitude
        )

        if similarity == 0:
            continue

        results.append({"id": document["id"], "distance": similarity})

    return sorted(results, key=lambda x: x["distance"], reverse=True)


if __name__ == "__main__":
    if "initialize" not in st.session_state:
        init()
        st.session_state.initialize = True
        st.session_state.stopwords = stopwords
        st.session_state.punctuations = punctuations
        st.session_state.index = index
    else:
        stopwords = st.session_state.stopwords
        punctuations = st.session_state.punctuations
        index = st.session_state.index

    st.set_page_config(page_title="Tuoitre Search", layout="centered")

    cols = st.columns([1] * 3)
    logo = Image.open("logo.png")
    cols[1].image(logo, use_container_width=True)

    cols = st.columns([8, 2])
    query = cols[0].text_input("Query", placeholder="Enter your query here")
    top_k = cols[1].number_input("Top", value=100, min_value=1, max_value=1000)

    cols = st.columns([1] * 3)
    search_clicked = cols[1].button("Search", use_container_width=True)

    if search_clicked:
        query = query.strip()

        if not query:
            st.warning("Please enter something to search")
        else:
            start_time = time.time()
            results = search_by_cosine_similarity(query)
            end_time = time.time()
            if not results:
                st.write(f"No results found in {end_time - start_time:.3f}s")
            else:
                st.write(
                    f"Found {len(results)} results in {end_time - start_time:.3f}s, showing top {min(top_k, len(results))}"
                )

                for i, result in enumerate(results[:top_k]):
                    with st.container():
                        cols = st.columns([1, 3])
                        with open(
                            f"data/{result['id']}.json", "r", encoding="utf-8"
                        ) as f:
                            data = json.load(f)

                            image = data["images"][0] if data["images"] else None
                            if image:
                                cols[0].image(image, use_container_width=True)
                            else:
                                cols[0].write("No image available")

                            description = data["description"]
                            if len(description) > 150:
                                description = description[:150] + "..."

                            cols[1].markdown(f"**{data['title']}**\n\n{description}")
