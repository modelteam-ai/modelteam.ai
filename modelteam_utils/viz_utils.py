import json
import os
from datetime import datetime, timedelta

from matplotlib import pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from wordcloud import WordCloud

from .constants import USER, REPO, STATS, SKILLS, LANGS, TIME_SERIES, ADDED, DELETED, PROFILES, NR_SKILLS
from .utils import get_extension_to_language_map, yyyy_mm_to_quarter


def generate_tag_cloud(skill_map, file_name):
    if len(skill_map) > 20:
        skill_map = dict(sorted(skill_map.items(), key=lambda item: item[1], reverse=True)[:20])
    wordcloud = WordCloud(width=800, height=400, background_color='white').generate_from_frequencies(skill_map)
    # Display the generated word cloud
    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    plt.title("Top Skills", fontsize=24)
    plt.savefig(file_name)


def to_short_date(yyyymm):
    mon_str = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    month = int(yyyymm[4:6])
    return f"{mon_str[month - 1]}\n{yyyymm[:4]}"


def generate_ts_plot(ts_stats, file_name, language, quarters):
    # Extract added values
    added = [ts_stats.get(key, [0, 0])[0] for key in quarters]
    disp_quarters = [q.replace('Q', '\nQ') for q in quarters]

    # Plotting
    plt.figure(figsize=(10, 5))
    plt.bar(disp_quarters, added, color='orange')
    plt.ylim(top=5000)
    plt.xlabel('Time', fontsize=15)
    plt.ylabel('Lines Added', fontsize=15)
    plt.title(language, fontsize=24)
    plt.tick_params(axis='both', which='major', labelsize=12)
    # plt.grid(True, axis='x', linestyle='-')
    plt.grid(True, axis='y', linestyle='-')
    plt.tight_layout()
    plt.savefig(file_name)


def trunc_string(s, max_len):
    max_len = max_len - 3
    return s if len(s) <= max_len else s[:max_len] + "..."


def generate_repo_plot(repo_qtr_stats, quarters, repo_stats_file_name):
    # Generate Line chart for with a line for each repo
    plt.figure(figsize=(10, 5))
    plt.xlabel('Time', fontsize=15)
    plt.ylabel('Lines Added', fontsize=15)
    plt.title("Repo Stats", fontsize=24)
    plt.tick_params(axis='both', which='major', labelsize=12)
    plt.grid(True, axis='y', linestyle='-')
    for repo in repo_qtr_stats.keys():
        vals = []
        for qtr in quarters:
            vals.append(repo_qtr_stats[repo].get(qtr, 0))
        plt.plot(quarters, vals, label=repo)
    plt.legend()
    plt.tight_layout()
    plt.savefig(repo_stats_file_name)


def add_commit_info_to_canvas(canvas_obj, user, repo, repo_data):
    top = pdf_header(canvas_obj, user)
    canvas_obj.setFont("Courier", 18)
    canvas_obj.drawString(50, top, f"Repo (#lines added): {repo}")
    top -= 30
    file_stats = repo_data["files"]
    canvas_obj.setFont("Courier", 15)
    canvas_obj.drawString(50, top, "Major Commits")
    top -= 20
    top_10_commits = sorted(repo_data["big_commits"].items(), key=lambda x: x[1], reverse=True)[:10]
    canvas_obj.setFont("Courier", 12)
    for commit in top_10_commits:
        canvas_obj.drawString(50, top, f"{commit[0]}: {commit[1]}")
        top -= 20
    top_file_count = 3
    for qtr in sorted(file_stats.keys(), reverse=True):
        if top < 50 + (top_file_count + 2) * 20:
            canvas_obj.showPage()
            top = pdf_header(canvas_obj, user)
            canvas_obj.setFont("Courier", 18)
            canvas_obj.drawString(50, top, f"Repo (#lines added): {repo} [contd.]")
            top -= 30
        l1stats = {}
        l2stats = {}
        canvas_obj.setFont("Courier", 15)
        top -= 20
        canvas_obj.drawString(50, top, f"Quarter: {qtr}")
        top -= 20
        for file in file_stats[qtr]:
            parts = os.path.normpath(file).split(os.sep)
            if len(parts) > 0:
                l1 = trunc_string(parts[0], 30)
                if l1 not in l1stats:
                    l1stats[l1] = 0
                l1stats[l1] += file_stats[qtr][file]
            if len(parts) > 1:
                l2 = trunc_string(f"{parts[0]}{os.sep}{parts[1]}", 30)
                if l2 not in l2stats:
                    l2stats[l2] = 0
                l2stats[l2] += file_stats[qtr][file]
        top_n_l1 = sorted(l1stats.items(), key=lambda x: x[1], reverse=True)[:top_file_count]
        top_n_l2 = sorted(l2stats.items(), key=lambda x: x[1], reverse=True)[:top_file_count]
        # filter < 50 lines
        top_n_l1 = [l1 for l1 in top_n_l1 if l1[1] > 50]
        top_n_l2 = [l2 for l2 in top_n_l2 if l2[1] > 50]
        # Display top 3 l2 and l1 as a table
        canvas_obj.setFont("Courier", 12)
        middle_of_a_line = 300
        for i in range(min(top_file_count, max(len(top_n_l1), len(top_n_l2)))):
            if i < len(top_n_l1):
                l1 = top_n_l1[i]
                canvas_obj.drawString(50, top, f"{l1[0]}: {l1[1]}")
            if i < len(top_n_l2):
                l2 = top_n_l2[i]
                canvas_obj.drawString(middle_of_a_line, top, f"{l2[0]}: {l2[1]}")
            top -= 20
    canvas_obj.showPage()


def generate_pdf_report(merged_json_file, pdf_stats_file, output_path):
    if not os.path.exists(output_path):
        os.makedirs(output_path, exist_ok=True)
    curr_date = datetime.now()
    qtr_iter = curr_date.replace(year=curr_date.year - 2)
    quarters = []
    while qtr_iter < curr_date:
        quarters.append(yyyy_mm_to_quarter(int(qtr_iter.strftime("%Y%m"))))
        qtr_iter += timedelta(days=90)
    lang_map = get_extension_to_language_map()
    merged_skills = {}
    repo_list = []
    merged_lang_stats = {}
    wc_file = os.path.join(output_path, "wordcloud.png")
    image_files = []
    with open(merged_json_file, "r") as f:
        merged_profile = json.load(f)
        user = merged_profile[USER]
        for user_stats in merged_profile[PROFILES]:
            repo = user_stats[REPO]
            non_relevant_skills = set(user_stats[NR_SKILLS])
            repo_list.append(repo)
            user_profile = user_stats[STATS]
            if SKILLS in user_profile:
                for s in user_profile[SKILLS]:
                    if s in non_relevant_skills:
                        continue
                    if s not in merged_skills:
                        merged_skills[s] = 0
                    merged_skills[s] += user_profile[SKILLS][s]
            lang_stats = user_profile[LANGS]
            lang_list = lang_stats.keys()
            for lang in lang_list:
                disp_lang = lang_map[lang] if lang in lang_map else lang
                if disp_lang not in merged_lang_stats:
                    merged_lang_stats[disp_lang] = {}
                if TIME_SERIES in lang_stats[lang]:
                    time_series = lang_stats[lang][TIME_SERIES]
                    for yyyy_mm in time_series:
                        qtr = yyyy_mm_to_quarter(int(yyyy_mm))
                        if qtr not in lang_stats[lang]:
                            merged_lang_stats[disp_lang][qtr] = [0, 0]
                        added = time_series[yyyy_mm][ADDED] if ADDED in time_series[yyyy_mm] else 0
                        deleted = time_series[yyyy_mm][DELETED] if DELETED in time_series[yyyy_mm] else 0
                        merged_lang_stats[disp_lang][qtr][0] += added
                        merged_lang_stats[disp_lang][qtr][1] += deleted
    if merged_lang_stats:
        for lang in merged_lang_stats:
            ts_stats = merged_lang_stats[lang]
            ts_file = os.path.join(output_path, f"{lang}_ts.png")
            generate_ts_plot(ts_stats, ts_file, lang, quarters)
            image_files.append(ts_file)
    if merged_skills:
        generate_tag_cloud(merged_skills, wc_file)
        image_files.append(wc_file)
    with open(pdf_stats_file, "r") as f:
        pdf_stats = json.load(f)
    repo_qtr_stats = {}
    for repo in pdf_stats.keys():
        repo_qtr_stats[repo] = {}
        for qtr in pdf_stats[repo]["files"]:
            repo_qtr_stats[repo][qtr] = sum(pdf_stats[repo]["files"][qtr].values())
    repo_stats_file_name = os.path.join(output_path, "repo_stats.png")
    generate_repo_plot(repo_qtr_stats, quarters, repo_stats_file_name)
    image_files.append(repo_stats_file_name)
    pdf_file = os.path.join(output_path, "modelteam_profile.pdf")
    c = canvas.Canvas(pdf_file, pagesize=letter)
    c.setFont("Courier", 12)
    add_images_to_canvas(c, user, image_files)
    for repo in pdf_stats.keys():
        add_commit_info_to_canvas(c, user, repo, pdf_stats[repo])
    c.save()
    print('!' * 50)
    print("PDF report generated. This is for your personal use only and is not needed by modelteam.ai.")
    print(pdf_file)
    print('!' * 50)


def generate_multi_page_pdf(output_path, user, image_files):
    pdf_file = os.path.join(output_path, "modelteam_profile.pdf")
    c = canvas.Canvas(pdf_file, pagesize=letter)
    add_images_to_canvas(c, user, image_files)
    c.save()


def add_images_to_canvas(canvas_obj, user, image_files):
    canvas_obj.setFont("Courier", 18)
    top = pdf_header(canvas_obj, user)
    image_height = 200
    image_margin = 10
    for image_file in image_files:
        if os.path.exists(image_file):
            if top < image_height + 50:
                canvas_obj.showPage()
                canvas_obj.setFont("Courier", 18)
                top = pdf_header(canvas_obj, user)
            top -= image_height
            canvas_obj.drawImage(image_file, 50, top, width=500, height=image_height)
            top -= image_margin
    canvas_obj.showPage()


def pdf_header(c, user):
    top = letter[1] - 30
    c.setFont("Courier", 12)
    c.setFillColor(colors.red)
    warn1 = "This is for your personal use. Do not share this with modelteam.ai."
    warn2 = "This is summary of your contributions in the past 2 years."
    c.drawString(50, top, warn1)
    c.drawString(50, top - 20, warn2)
    top -= 50
    c.setFillColor(colors.black)
    c.setFont("Courier", 24)
    c.drawString(50, top, "modelteam.ai")
    c.setFont("Courier-Bold", 12)
    c.drawString(250, top, f"{user}")
    top -= 30
    return top
