import json
import os

from matplotlib import pyplot as plt
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from wordcloud import WordCloud

from .constants import USER, REPO, STATS, SKILLS, LANGS, TIME_SERIES, ADDED, DELETED, PROFILES
from .utils import get_extension_to_language_map


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


def generate_ts_plot(ts_stats, file_name):
    years_months = sorted(ts_stats.keys())
    readable_dates = []
    for yyyymm in years_months:
        readable_dates.append(to_short_date(yyyymm))

    # Extract added and deleted values
    added = [ts_stats[key][0] for key in years_months]
    deleted = [ts_stats[key][1] for key in years_months]

    # Plotting
    plt.figure(figsize=(10, 5))
    plt.plot(readable_dates, added, label='Lines Added')
    plt.plot(readable_dates, deleted, label='Lines Deleted')

    plt.xlabel('Time', fontsize=15)
    plt.ylabel('Count', fontsize=15)
    plt.title('Code Contribution Over Time', fontsize=24)
    plt.tick_params(axis='both', which='major', labelsize=12)
    plt.legend(fontsize=15)
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(file_name)


def generate_pdf(output_path, user, repo, languages, image_files):
    pdf_file = os.path.join(output_path, f"{user}.pdf")
    c = canvas.Canvas(pdf_file, pagesize=letter)
    c.setFont("Helvetica", 24)
    c.drawString(50, 700, "ModelTeam.AI")
    c.setFont("Helvetica", 12)
    c.drawString(50, 650, f"User: {user}")
    c.drawString(50, 630, f"Repo: {repo}")
    c.drawString(50, 610, f"Languages: {','.join(languages)}")
    top = 400
    for image_file in image_files:
        c.drawImage(image_file, 50, top, width=500, height=200)
        top -= 250
    c.save()


def generate_pdf_report(merged_json, output_path):
    lang_map = get_extension_to_language_map()
    merged_skills = {}
    repo_list = []
    merged_lang_stats = {}
    wc_file = os.path.join(output_path, "wordcloud.png")
    image_files = []
    with open(merged_json, "r") as f:
        merged_profile = json.load(f)
        for user_stats in merged_profile[PROFILES]:
            user = user_stats[USER]
            repo = user_stats[REPO]
            repo_list.append(repo)
            user_profile = user_stats[STATS]
            if SKILLS in user_profile:
                for s in user_profile[SKILLS]:
                    if s not in merged_skills:
                        merged_skills[s] = 0
                    merged_skills[s] += user_profile[SKILLS][s]
            lang_stats = user_profile[LANGS]
            lang_list = lang_stats.keys()
            for lang in lang_list:
                if lang not in merged_lang_stats:
                    merged_lang_stats[lang] = {}
                if TIME_SERIES in lang_stats[lang]:
                    time_series = lang_stats[lang][TIME_SERIES]
                    for yyyy_mm in time_series:
                        if yyyy_mm not in lang_stats[lang]:
                            merged_lang_stats[lang][yyyy_mm] = [0, 0]
                        added = time_series[yyyy_mm][ADDED] if ADDED in time_series[yyyy_mm] else 0
                        deleted = time_series[yyyy_mm][DELETED] if DELETED in time_series[yyyy_mm] else 0
                        merged_lang_stats[lang][yyyy_mm][0] += added
                        merged_lang_stats[lang][yyyy_mm][1] += deleted
    if merged_skills:
        generate_tag_cloud(merged_skills, wc_file)
        image_files.append(wc_file)
    lang_names = []
    if merged_lang_stats:
        for lang in merged_lang_stats:
            ts_stats = merged_lang_stats[lang]
            ts_file = os.path.join(output_path, f"{lang}_ts.png")
            generate_ts_plot(ts_stats, ts_file)
            image_files.append(ts_file)
        lang_names = [lang_map[lang] for lang in merged_lang_stats.keys()]
    generate_multi_page_pdf(output_path, user, image_files)


def generate_multi_page_pdf(output_path, user, image_files):
    pdf_file = os.path.join(output_path, f"{user}.pdf")
    c = canvas.Canvas(pdf_file, pagesize=letter)
    c.setFont("Helvetica", 18)
    page_height = letter[1]
    top = page_height - 50
    top = pdf_header(c, top, user)
    image_height = 200
    image_margin = 25
    for image_file in image_files:
        if os.path.exists(image_file):
            if top < image_height + image_margin:
                c.showPage()
                c.setFont("Helvetica", 18)
                pdf_header(c, top, user)
                top = page_height - 50
            top -= (image_height + image_margin)
            c.drawImage(image_file, 50, top, width=500, height=image_height)
    c.save()


def pdf_header(c, top, user):
    c.drawString(50, top, "modelteam.ai")
    c.setFont("Helvetica-Bold", 16)
    top -= 50
    c.drawString(50, top, f"Summary for {user}")
    return top
