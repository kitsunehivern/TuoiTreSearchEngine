import os
import requests
from bs4 import BeautifulSoup
import json

input_url_list = input(
    "Please enter the URLs, separated by space (e.g. https://tuoitre.vn/giao-duc.htm): "
)

input_urls = input_url_list.split(" ")
for input_url in input_urls:
    if not input_url.startswith("https://tuoitre.vn/"):
        print(f"URL {input_url} is not valid")

input_number_list = input(
    "Please enter the number of posts you want to crawl from each URL, separated by space: "
)

input_numbers = list(map(int, input_number_list.split(" ")))
for input_number in input_numbers:
    if input_number <= 0:
        print(f"Number of posts {input_number} is not valid")

if len(input_urls) != len(input_numbers):
    print("Number of URLs and number of posts are not equal")
    exit()

url = "https://tuoitre.vn"

timeline = {
    "thoi-su.htm": 3,
    "the-gioi.htm": 2,
    "phap-luat.htm": 6,
    "kinh-doanh.htm": 11,
    "cong-nghe.htm": 200029,
    "xe.htm": 659,
    "du-lich.htm": 100,
    "nhip-song-tre.htm": 7,
    "van-hoa.htm": 200017,
    "giai-tri.htm": 10,
    "the-thao.htm": 1209,
    "giao-duc.htm": 13,
    "nha-dat.htm": 204,
    "suc-khoe.htm": 12,
    "gia-that.htm": 200015,
    "ban-doc-lam-bao.htm": 118,
}

for input_url, input_number in zip(input_urls, input_numbers):
    category_url = input_url.split("/")[-1]
    if category_url not in timeline:
        print(f"URL {input_url} is not supported")
        continue

    category_url = url + "/timeline/" + str(timeline[category_url])
    page_index = 1
    while input_number > 0:
        print(f"Crawling data from {category_url} page {page_index}")
        response = requests.get(category_url + f"/trang-{page_index}.htm")

        if response.status_code != 200:
            print(f"Failed to crawl data from {category_url} page {page_index}.")
            exit()

        print("Extracting urls and ids")
        soup = BeautifulSoup(response.content, "html.parser")
        titles = soup.findAll("h3", class_="box-title-text")
        links = [title.find("a").attrs.get("href") for title in titles]
        ids = [title.attrs.get("data-comment") for title in titles]

        for i, link in enumerate(links):
            print(f"Crawling content from {url + link}")

            if os.path.exists(f"data/{ids[i]}.json"):
                print(f"Data from {url + link} has been saved before")
                continue

            response = requests.get(url + link)
            if response.status_code != 200:
                print(f"Failed to crawl data from {url + link}")
                continue

            soup = BeautifulSoup(response.content, "html.parser")

            # Extract data
            print("Extracting data")
            author = soup.find("meta", property="dable:author").attrs.get("content")
            date = soup.find("meta", property="article:published_time").attrs.get(
                "content"
            )
            title = soup.find("meta", property="og:title").attrs.get("content")
            description = soup.find("meta", property="og:description").attrs.get(
                "content"
            )
            author = soup.find("meta", property="dable:author").attrs.get("content")
            category = soup.find("meta", property="article:section").attrs.get(
                "content"
            )

            body = soup.find("div", class_="detail-content afcbc-body")
            if not body:
                body = soup.find(
                    "div", class_="detail-content contentOuter sp-detail-content"
                )

            description = description.replace("\r\n", "").strip()
            content = " ".join([p.text for p in body.findAll("p", recursive=False)])

            image_urls = [
                image_url.attrs.get("src") for image_url in body.findAll("img")
            ]

            audio_url = (
                "https://tts.mediacdn.vn/"
                + date.split("T")[0].replace("-", "/")
                + "/tuoitre-nu-1-"
                + ids[i]
                + ".m4a"
            )

            # Crawl reactions
            print("Crawling reactions")
            response = requests.get(
                f"https://s5.tuoitre.vn/showvote-reaction.htm?newsid={ids[i]}&m=viewreact"
            )

            reaction_data = response.json()["Data"]
            reactions = {
                "stars": 0,
                "likes": 0,
                "loves": 0,
            }

            if reaction_data:
                for reaction in reaction_data:
                    if reaction["Type"] == 2:
                        reactions["loves"] = reaction["TotalStar"]
                    elif reaction["Type"] == 3:
                        reactions["likes"] = reaction["TotalStar"]
                    else:
                        reactions["stars"] = reaction["TotalStar"]

            # Crawl comments
            print("Crawling comments")
            comment_index = 1
            comments_data = []
            while True:
                print(f"Loading comments page {comment_index}")
                response = requests.get(
                    f"https://id.tuoitre.vn/api/getlist-comment.api?objId={ids[i]}&objType=1&pageindex={comment_index}"
                )

                data = json.loads(response.json()["Data"])
                if len(data) == 0:
                    break

                comments_data.extend(data)
                comment_index += 1

            comments = []
            for comment in comments_data:
                comments.append(
                    {
                        "commentId": comment["id"],
                        "author": comment["sender_fullname"],
                        "text": comment["content"],
                        "date": comment["published_date"],
                        "vote react list": {
                            "loves": comment["loves"],
                            "hahas": comment["hahas"],
                            "sads": comment["sads"],
                            "wows": comment["wows"],
                            "wraths": comment["wraths"],
                            "stars": comment["stars"],
                            "starts": comment["starts"],
                        },
                    }
                )

                comments[-1]["comment replies"] = []
                for reply in comment["child_comments"]:
                    comments[-1]["comment replies"].append(
                        {
                            "commentId": reply["id"],
                            "author": reply["sender_fullname"],
                            "text": reply["content"],
                            "date": reply["published_date"],
                            "vote react list": {
                                "loves": reply["loves"],
                                "hahas": reply["hahas"],
                                "sads": reply["sads"],
                                "wows": reply["wows"],
                                "wraths": reply["wraths"],
                                "stars": reply["stars"],
                                "starts": reply["starts"],
                            },
                        }
                    )

            # Crawl images
            # print("Crawling images")
            # images = []
            # for image_url in image_urls:
            #     image_name = image_url.split("/")[-1]
            #     image = requests.get(image_url)
            #     images.append(image)

            # Crawl audio
            # print("Crawling audio")
            # audio = requests.get(audio_url)

            # Save data
            print("Saving data")
            if not os.path.exists(f"data"):
                os.mkdir(f"data")

            with open(f"data/{ids[i]}.json", "w", encoding="utf-8") as file:
                json.dump(
                    {
                        "postId": ids[i],
                        "title": title,
                        "description": description,
                        "content": content,
                        "author": author,
                        "date": date,
                        "category": category,
                        "audio podcast": audio_url,
                        "images": image_urls,
                        "vote react list": reactions,
                        "comments": comments,
                    },
                    file,
                    ensure_ascii=False,
                )

            # Save images
            # print("Saving images")
            # if not os.path.exists(f"images"):
            #     os.mkdir(f"images")

            # if not os.path.exists(f"images/{ids[i]}"):
            #     os.mkdir(f"images/{ids[i]}")

            # for j, image_url in enumerate(image_urls):
            #     image_name = image_url.split("/")[-1]
            #     with open(f"images/{ids[i]}/{image_name}", "wb") as file:
            #         file.write(images[j].content)

            # Save audio
            # print("Saving audio")
            # if not os.path.exists(f"audio"):
            #     os.mkdir(f"audio")

            # with open(f"audio/{ids[i]}.m4a", "wb") as file:
            #     file.write(audio.content)

            print(f"All data from {url + link} has been saved successfully.")

            input_number -= 1
            if input_number == 0:
                break

        page_index += 1

    print(f"All data from {input_url} has been saved successfully.")
print("All data has been saved successfully.")
