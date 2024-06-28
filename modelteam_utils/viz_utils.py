from matplotlib import pyplot as plt
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from wordcloud import WordCloud


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
    pdf_file = f"{output_path}/{user}.pdf"
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
