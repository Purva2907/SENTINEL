with open('frontend/case-detail.html', 'r', encoding='utf-8') as f:
    html = f.read()

ids = [
    'loading', 'caseContent', 'genReportBtn', 'downloadBtn', 'caseHeader',
    'cTitle', 'cDesc', 'cStatus', 'cCreated', 'scoreCardContainer',
    'cScore', 'cClass', 'cClassSubtitle', 'cRiskLabel', 'cRec',
    'cHeatmap', 'cOriginal', 'cHeatmapFallback', 'mQualScore', 'mQualFind',
    'mOcr', 'mQrStatus', 'mQrPayloadType', 'mQrDataPreview', 'mQrDetectCount',
    'mQrConsistRow', 'mQrConsist', 'evidenceTimelineFeed', 'investigationTimelineFeed',
    'notesList'
]

for i in ids:
    if f'id="{i}"' not in html and f"id='{i}'" not in html:
        print('MISSING ID:', i)
print('Done checking IDs')
