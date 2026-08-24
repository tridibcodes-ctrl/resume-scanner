/**
 * Smart Resume Screener — Main Application
 * 
 * Handles file uploads, API communication, result rendering,
 * and the candidate detail modal.
 */

import './style.css';
import { api } from './api.js';

// ─── State ──────────────────────────────────────────────────────────────────

const state = {
    files: [],
    sessionId: null,
    results: null,
};

// ─── Sample JD ──────────────────────────────────────────────────────────────

const SAMPLE_JD = `Senior Software Engineer

About the Role
We are looking for a Senior Software Engineer to join our Product Engineering team. You will design, build, and maintain scalable web applications that serve millions of users.

Requirements
- 5+ years of professional software development experience
- Strong proficiency in JavaScript/TypeScript and at least one backend language (Python, Java, or Go)
- Experience with modern frontend frameworks (React, Angular, or Vue.js)
- Experience with Node.js or similar server-side JavaScript runtime
- Solid understanding of relational databases (PostgreSQL, MySQL) and NoSQL databases (MongoDB, Redis)
- Experience with cloud services (AWS, GCP, or Azure)
- Familiarity with containerization (Docker) and orchestration (Kubernetes)
- Experience with CI/CD pipelines and automated testing
- Strong understanding of RESTful API design and microservices architecture
- Bachelor's degree in Computer Science or related field

Nice to Have
- Experience with GraphQL
- Knowledge of infrastructure-as-code (Terraform, CloudFormation)
- Experience with real-time systems (WebSockets, event-driven architecture)
- Contributions to open-source projects
- Experience mentoring junior engineers

Responsibilities
- Design and implement scalable, maintainable backend services and APIs
- Build responsive, performant user interfaces using modern frontend frameworks
- Collaborate with cross-functional teams to define technical requirements
- Participate in code reviews and contribute to engineering best practices
- Monitor application performance and troubleshoot production issues
- Mentor junior team members and contribute to a culture of technical excellence`;

const SAMPLE_RESUMES = [
    {
        name: 'alice_johnson_senior_dev.txt',
        content: `Alice Johnson\nalice.johnson@email.com | (555) 123-4567\nLinkedIn: linkedin.com/in/alicejohnson | GitHub: github.com/alicejohnson\n\nPROFESSIONAL SUMMARY\nSenior Full-Stack Software Engineer with 8+ years of experience building scalable web applications. Passionate about clean architecture, performance optimization, and mentoring junior developers.\n\nSKILLS\nJavaScript, TypeScript, Python, Java, React, React.js, Next.js, Node.js, Express.js, Django, PostgreSQL, MongoDB, Redis, AWS, Docker, Kubernetes, CI/CD, GitHub Actions, GraphQL, REST APIs, HTML, CSS, Git, Agile, Microservices, Jest, Pytest\n\nEXPERIENCE\nSenior Software Engineer | TechCorp Inc.\nJan 2021 - Present\n- Lead a team of 6 engineers building a real-time analytics platform serving 2M+ daily active users\n- Architected microservices infrastructure using Node.js, React, and AWS\n- Reduced API response time by 40% through Redis caching and query optimization\n\nEDUCATION\nBachelor of Science in Computer Science\nMassachusetts Institute of Technology (MIT)\nGraduated: 2016`
    },
    {
        name: 'bob_kumar_devops.txt',
        content: `Bob Kumar\nbob.kumar@email.com | (555) 234-5678\nLinkedIn: linkedin.com/in/bobkumar\n\nSUMMARY\nDevOps Engineer with 5 years of experience in cloud infrastructure, automation, and CI/CD pipeline management.\n\nSKILLS\nDocker, Kubernetes, AWS, Azure, Terraform, Ansible, Jenkins, GitHub Actions, Python, Bash, Linux, Nginx, Prometheus, Grafana, PostgreSQL, Redis, Git\n\nEXPERIENCE\nSenior DevOps Engineer | CloudFirst Solutions\nJul 2022 - Present\n- Manage Kubernetes clusters across AWS EKS for a fintech platform\n- Built infrastructure-as-code using Terraform\n\nEDUCATION\nBachelor of Technology in Information Technology\nIIT Delhi\nGraduated: 2019`
    },
    {
        name: 'carol_chen_junior_analyst.txt',
        content: `Carol Chen\ncarol.chen@email.com | (555) 345-6789\n\nSUMMARY\nJunior Data Analyst with 1 year of experience in data visualization and statistical analysis.\n\nSKILLS\nPython, SQL, R, Pandas, NumPy, Tableau, Power BI, Excel, PostgreSQL\n\nEDUCATION\nBachelor of Science in Statistics\nUCLA\nGraduated: 2023`
    },
    {
        name: 'dave_wilson_marketing.txt',
        content: `Dave Wilson\ndave.wilson@email.com | (555) 456-7890\n\nSUMMARY\nMarketing Director with 7 years of experience in digital marketing and campaign management.\n\nSKILLS\nDigital Marketing, SEO, SEM, Content Strategy, Google Analytics, Social Media Marketing\n\nEDUCATION\nBachelor of Arts in Communications\nNYU\nGraduated: 2017`
    }
];

// ─── DOM Elements ───────────────────────────────────────────────────────────

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const dom = {
    resumeDropzone: $('#resume-dropzone'),
    resumeInput: $('#resume-input'),
    loadSampleResumes: $('#load-sample-resumes'),
    fileList: $('#file-list'),
    jdTextarea: $('#jd-textarea'),
    jdCharCount: $('#jd-char-count'),
    loadSampleJd: $('#load-sample-jd'),
    analyzeBtn: $('#analyze-btn'),
    analyzeInfo: $('#analyze-info'),
    resumeCount: $('#resume-count'),
    jdStatus: $('#jd-status'),
    uploadSection: $('#upload-section'),
    progressSection: $('#progress-section'),
    progressDetail: $('#progress-detail'),
    progressBar: $('#progress-bar'),
    progressSteps: $('#progress-steps'),
    resultsSection: $('#results-section'),
    resultsMeta: $('#results-meta'),
    resultsGrid: $('#results-grid'),
    modalOverlay: $('#modal-overlay'),
    modalContent: $('#modal-content'),
    modalClose: $('#modal-close'),
};

// ─── Initialize ─────────────────────────────────────────────────────────────

function init() {
    setupDropzone();
    setupSampleResumesButton();
    setupJdTextarea();
    setupAnalyzeButton();
    setupModal();
}

function setupSampleResumesButton() {
    if (!dom.loadSampleResumes) return;
    dom.loadSampleResumes.addEventListener('click', () => {
        const files = SAMPLE_RESUMES.map(r => new File([r.content], r.name, { type: 'text/plain' }));
        addFiles(files);
    });
}

// ─── Dropzone ───────────────────────────────────────────────────────────────

function setupDropzone() {
    const dz = dom.resumeDropzone;
    const input = dom.resumeInput;

    dz.addEventListener('click', () => input.click());

    dz.addEventListener('dragover', (e) => {
        e.preventDefault();
        dz.classList.add('drag-over');
    });

    dz.addEventListener('dragleave', () => {
        dz.classList.remove('drag-over');
    });

    dz.addEventListener('drop', (e) => {
        e.preventDefault();
        dz.classList.remove('drag-over');
        addFiles(e.dataTransfer.files);
    });

    input.addEventListener('change', () => {
        addFiles(input.files);
        input.value = '';
    });
}

function addFiles(fileList) {
    const allowed = ['.pdf', '.txt'];
    const maxSize = 5 * 1024 * 1024;

    for (const file of fileList) {
        const ext = '.' + file.name.split('.').pop().toLowerCase();
        if (!allowed.includes(ext)) {
            alert(`Unsupported file type: ${ext}. Use PDF or TXT.`);
            continue;
        }
        if (file.size > maxSize) {
            alert(`${file.name} exceeds 5MB limit.`);
            continue;
        }
        if (state.files.length >= 10) {
            alert('Maximum 10 resumes per session.');
            break;
        }
        if (!state.files.find(f => f.name === file.name)) {
            state.files.push(file);
        }
    }

    renderFileList();
    updateAnalyzeState();
}

function removeFile(index) {
    state.files.splice(index, 1);
    renderFileList();
    updateAnalyzeState();
}

function renderFileList() {
    dom.fileList.innerHTML = state.files.map((file, i) => `
        <div class="file-item">
            <div class="file-item-info">
                <div class="file-type-badge">${file.name.endsWith('.pdf') ? 'PDF' : 'TXT'}</div>
                <div class="file-item-details">
                    <span class="file-item-name">${file.name}</span>
                    <span class="file-item-size">${formatSize(file.size)}</span>
                </div>
            </div>
            <button class="file-item-remove" data-index="${i}" title="Remove">×</button>
        </div>
    `).join('');

    dom.fileList.querySelectorAll('.file-item-remove').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            removeFile(parseInt(btn.dataset.index));
        });
    });
}

// ─── JD Textarea ────────────────────────────────────────────────────────────

function setupJdTextarea() {
    dom.jdTextarea.addEventListener('input', () => {
        const len = dom.jdTextarea.value.length;
        dom.jdCharCount.textContent = `${len} characters`;
        updateAnalyzeState();
    });

    dom.loadSampleJd.addEventListener('click', () => {
        dom.jdTextarea.value = SAMPLE_JD;
        dom.jdCharCount.textContent = `${SAMPLE_JD.length} characters`;
        updateAnalyzeState();
    });
}

// ─── Analyze State ──────────────────────────────────────────────────────────

function updateAnalyzeState() {
    const hasFiles = state.files.length > 0;
    const hasJd = dom.jdTextarea.value.trim().length >= 10;

    dom.resumeCount.textContent = `${state.files.length} resume${state.files.length !== 1 ? 's' : ''}`;
    dom.jdStatus.textContent = hasJd ? 'JD ready' : 'No JD';
    dom.jdStatus.style.color = hasJd ? 'hsl(152 40% 36%)' : '';

    dom.analyzeBtn.disabled = !(hasFiles && hasJd);
}

// ─── Analyze Button ─────────────────────────────────────────────────────────

function setupAnalyzeButton() {
    dom.analyzeBtn.addEventListener('click', runAnalysis);
}

async function runAnalysis() {
    const btnText = dom.analyzeBtn.querySelector('.btn-text');
    const btnLoader = dom.analyzeBtn.querySelector('.btn-loader');

    try {
        // Show progress
        dom.analyzeBtn.disabled = true;
        btnText.hidden = true;
        btnLoader.hidden = false;
        dom.progressSection.hidden = false;
        dom.resultsSection.hidden = true;

        // Scroll to progress
        dom.progressSection.scrollIntoView({ behavior: 'smooth' });

        // Step 1: Create session
        updateProgress('upload', 'active', 'Creating session…', 10);
        const { session_id } = await api.createSession();
        state.sessionId = session_id;

        // Step 2: Upload resumes
        updateProgress('upload', 'active', 'Uploading resumes…', 25);
        await api.uploadResumes(session_id, state.files);
        updateProgress('upload', 'done', 'Resumes uploaded', 35);

        // Step 3: Submit JD
        updateProgress('jd', 'active', 'Submitting job description…', 45);
        await api.submitJobDescription(session_id, dom.jdTextarea.value.trim());
        updateProgress('jd', 'done', 'Job description parsed', 55);

        // Step 4: Analyze
        updateProgress('analyze', 'active', 'Running AI analysis (this may take 15–30s)…', 65);
        const results = await api.analyze(session_id);
        updateProgress('analyze', 'done', 'Analysis complete', 100);

        // Show results
        state.results = results;
        await new Promise(r => setTimeout(r, 500)); // Brief pause for UX
        renderResults(results);
    } catch (err) {
        console.error('Analysis failed:', err);
        dom.progressDetail.textContent = `Error: ${err.message}`;
        dom.progressDetail.style.color = 'hsl(0 48% 48%)';
        alert(`Analysis failed: ${err.message}`);
    } finally {
        btnText.hidden = false;
        btnLoader.hidden = true;
        dom.analyzeBtn.disabled = false;
    }
}

function updateProgress(step, status, detail, pct) {
    dom.progressDetail.textContent = detail;
    dom.progressBar.style.width = `${pct}%`;

    const stepEl = dom.progressSteps.querySelector(`[data-step="${step}"]`);
    if (stepEl) {
        stepEl.className = `progress-step ${status}`;
    }
}

// ─── Render Results ─────────────────────────────────────────────────────────

function renderResults(results) {
    dom.progressSection.hidden = true;
    dom.resultsSection.hidden = false;

    dom.resultsMeta.textContent = `${results.total_candidates} candidates · ${results.job_title || 'Job'}`;

    dom.resultsGrid.innerHTML = results.candidates.map((c, i) => {
        const score = c.match_analysis.overall_score;
        const cls = c.match_analysis.classification;
        const badgeClass = cls === 'Strong Match' ? 'badge-strong' :
                          cls === 'Moderate Match' ? 'badge-moderate' : 'badge-weak';
        const pillColor = scorePillColor(score);
        const topSkills = c.match_analysis.matched_skills.slice(0, 3);

        return `
        <div class="candidate-card clay-surface" data-index="${i}" style="animation-delay: ${i * 0.1}s">
            <div class="candidate-card-info">
                <div class="candidate-card-header">
                    <span class="candidate-rank">#${i + 1}</span>
                    <span class="candidate-name">${c.name || 'Unknown'}</span>
                    <span class="classification-badge ${badgeClass}">${cls}</span>
                </div>
                <div class="candidate-filename">${c.filename}</div>
                <div class="candidate-skills-preview">
                    ${topSkills.map(s => `<span class="skill-tag matched">${s.required_skill}</span>`).join('')}
                    ${c.match_analysis.missing_skills.slice(0, 2).map(s => `<span class="skill-tag missing">${s}</span>`).join('')}
                </div>
            </div>
            <div class="candidate-card-actions">
                <div class="score-pill" style="background:${pillColor.bg};color:${pillColor.text}">${score}</div>
                <button class="view-details-btn" data-index="${i}">View Details</button>
            </div>
        </div>`;
    }).join('');

    // Add click handlers
    dom.resultsGrid.querySelectorAll('.candidate-card').forEach(card => {
        card.addEventListener('click', () => {
            const idx = parseInt(card.dataset.index);
            showDetail(results.candidates[idx]);
        });
    });

    dom.resultsSection.scrollIntoView({ behavior: 'smooth' });
}

// ─── Score Ring (Conic Gradient) ────────────────────────────────────────────

function renderScoreRing(score, size = 140) {
    const deg = score * 3.6;
    const innerSize = size - 30;
    const color = scoreColor(score);

    return `
        <div class="score-ring" style="width:${size}px;height:${size}px;background:conic-gradient(${color} 0deg ${deg}deg, hsl(34 28% 81%) ${deg}deg 360deg)">
            <div class="score-ring-inner" style="width:${innerSize}px;height:${innerSize}px">
                <div class="score-number" style="color:${color}">${score}</div>
                <div class="score-out-of">out of 100</div>
            </div>
        </div>
    `;
}

function scoreColor(score) {
    if (score >= 75) return 'hsl(152 40% 36%)';
    if (score >= 50) return 'hsl(35 54% 43%)';
    return 'hsl(0 45% 48%)';
}

function scorePillColor(score) {
    if (score >= 75) return { bg: 'hsl(152 30% 87%)', text: 'hsl(152 40% 30%)' };
    if (score >= 50) return { bg: 'hsl(35 40% 88%)', text: 'hsl(35 54% 33%)' };
    return { bg: 'hsl(0 34% 90%)', text: 'hsl(0 45% 42%)' };
}

function scoreBarColor(score) {
    if (score >= 75) return 'hsl(152 40% 36%)';
    if (score >= 50) return 'hsl(35 54% 43%)';
    return 'hsl(0 45% 48%)';
}

// ─── Detail Modal ───────────────────────────────────────────────────────────

function setupModal() {
    dom.modalClose.addEventListener('click', hideModal);
    dom.modalOverlay.addEventListener('click', (e) => {
        if (e.target === dom.modalOverlay) hideModal();
    });
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') hideModal();
    });
}

function hideModal() {
    dom.modalOverlay.classList.remove('visible');
    document.body.style.overflow = '';
}

function showDetail(candidate) {
    const c = candidate;
    const m = c.match_analysis;
    const r = c.parsed_resume;
    const score = m.overall_score;
    const cls = m.classification;
    const badgeClass = cls === 'Strong Match' ? 'badge-strong' :
                      cls === 'Moderate Match' ? 'badge-moderate' : 'badge-weak';

    // Format resume text for display
    const resumeHtml = formatResumeText(c.raw_text || '', c.filename);

    // Build per-dimension analysis segments
    const segments = buildAnalysisSegments(m, r);

    dom.modalContent.innerHTML = `
        <!-- Compact Header -->
        <div class="detail-header">
            <div class="detail-header-left">
                ${renderScoreRing(score, 100)}
                <div class="detail-header-info">
                    <h2>${c.name || 'Unknown Candidate'}</h2>
                    <div class="detail-header-meta">
                        ${r.email ? `<span>${r.email}</span>` : ''}
                        ${r.phone ? `<span class="meta-separator">·</span><span>${r.phone}</span>` : ''}
                        ${r.total_years_experience ? `<span class="meta-separator">·</span><span>${r.total_years_experience} years exp.</span>` : ''}
                    </div>
                    <span class="classification-badge ${badgeClass}">${cls}</span>
                </div>
            </div>
        </div>

        <!-- Split Panel Layout -->
        <div class="detail-split">
            <!-- Left: Resume Viewer -->
            <div class="detail-panel detail-resume-panel">
                <div class="panel-header">
                    <h3>Resume</h3>
                    <span class="panel-filename">${c.filename}</span>
                </div>
                <div class="resume-viewer">
                    ${resumeHtml}
                </div>
            </div>

            <!-- Right: Segmented Analysis -->
            <div class="detail-panel detail-analysis-panel">
                <div class="panel-header">
                    <h3>Analysis</h3>
                </div>

                <!-- Assessment -->
                <div class="analysis-assessment">
                    <p>${m.justification}</p>
                </div>

                <!-- Dimension Segments -->
                ${segments}
            </div>
        </div>
    `;

    // Setup collapsible segments
    dom.modalContent.querySelectorAll('.segment-header').forEach(header => {
        header.addEventListener('click', () => {
            const segment = header.closest('.analysis-segment');
            segment.classList.toggle('collapsed');
        });
    });

    dom.modalOverlay.classList.add('visible');
    document.body.style.overflow = 'hidden';
}

function formatResumeText(rawText, filename) {
    if (!rawText || !rawText.trim()) {
        return '<div class="empty-state">Resume text not available</div>';
    }

    // Escape HTML
    let text = rawText
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    // Detect and highlight section headers (lines that look like headings)
    const sectionPatterns = [
        /^(PROFESSIONAL\s*SUMMARY|SUMMARY|PROFILE|OBJECTIVE|ABOUT\s*ME)/i,
        /^(SKILLS|TECHNICAL\s*SKILLS|CORE\s*COMPETENCIES|TECHNOLOGIES)/i,
        /^(EXPERIENCE|WORK\s*EXPERIENCE|PROFESSIONAL\s*EXPERIENCE|EMPLOYMENT)/i,
        /^(EDUCATION|ACADEMIC|QUALIFICATIONS)/i,
        /^(PROJECTS|PERSONAL\s*PROJECTS|KEY\s*PROJECTS)/i,
        /^(CERTIFICATIONS?|LICENSES?|AWARDS?|ACHIEVEMENTS?)/i,
        /^(PUBLICATIONS?|INTERESTS?|HOBBIES|VOLUNTEER|REFERENCES?)/i,
    ];

    const lines = text.split('\n');
    const formattedLines = lines.map(line => {
        const trimmed = line.trim();
        if (!trimmed) return '<div class="resume-line resume-blank">&nbsp;</div>';

        // Check if this line is a section header
        const isSection = sectionPatterns.some(p => p.test(trimmed));
        if (isSection) {
            return `<div class="resume-line resume-section-heading">${trimmed}</div>`;
        }

        // Check if line starts with bullet or dash
        if (/^[-•●▪▸►]\s/.test(trimmed) || /^\d+\.\s/.test(trimmed)) {
            return `<div class="resume-line resume-bullet">${trimmed}</div>`;
        }

        // First few non-empty lines are likely name/contact
        return `<div class="resume-line">${trimmed}</div>`;
    });

    return formattedLines.join('');
}

function buildAnalysisSegments(m, r) {
    const dimensions = [
        {
            key: 'skills',
            label: 'Skills Match',
            score: m.skills_score,
            icon: '◆',
            content: buildSkillsSegmentContent(m),
        },
        {
            key: 'experience',
            label: 'Experience Relevance',
            score: m.experience_score,
            icon: '▶',
            content: buildExperienceSegmentContent(m, r),
        },
        {
            key: 'education',
            label: 'Education Alignment',
            score: m.education_score,
            icon: '●',
            content: buildEducationSegmentContent(m, r),
        },
        {
            key: 'projects',
            label: 'Project Relevance',
            score: m.project_score,
            icon: '■',
            content: buildProjectsSegmentContent(m, r),
        },
    ];

    return dimensions.map(d => {
        const color = scoreBarColor(d.score);
        const pct = d.score;
        const verdict = d.score >= 75 ? 'Strong' : d.score >= 50 ? 'Adequate' : 'Weak';
        const verdictColor = d.score >= 75 ? 'hsl(152 40% 36%)' : d.score >= 50 ? 'hsl(35 54% 43%)' : 'hsl(0 45% 48%)';

        return `
            <div class="analysis-segment" data-segment="${d.key}">
                <div class="segment-header">
                    <div class="segment-header-left">
                        <span class="segment-icon" style="color: ${color}">${d.icon}</span>
                        <span class="segment-label">${d.label}</span>
                    </div>
                    <div class="segment-header-right">
                        <span class="segment-verdict" style="color: ${verdictColor}">${verdict}</span>
                        <span class="segment-score" style="color: ${color}">${pct}%</span>
                        <span class="segment-chevron">▾</span>
                    </div>
                </div>
                <div class="segment-bar">
                    <div class="segment-bar-fill" style="width: ${pct}%; background: ${color}"></div>
                </div>
                <div class="segment-body">
                    ${d.content}
                </div>
            </div>
        `;
    }).join('') + `
        <!-- Strengths & Weaknesses -->
        <div class="analysis-segment" data-segment="summary">
            <div class="segment-header">
                <div class="segment-header-left">
                    <span class="segment-icon" style="color: hsl(var(--accent))">★</span>
                    <span class="segment-label">Strengths & Gaps</span>
                </div>
                <div class="segment-header-right">
                    <span class="segment-chevron">▾</span>
                </div>
            </div>
            <div class="segment-body">
                <div class="sw-split">
                    <div>
                        <div class="sw-subheading" style="color: hsl(152 40% 36%)">Strengths</div>
                        ${m.strengths.map(s => `<div class="sw-item strength">${s}</div>`).join('')}
                    </div>
                    <div>
                        <div class="sw-subheading" style="color: hsl(0 45% 48%)">Gaps</div>
                        ${m.weaknesses.map(w => `<div class="sw-item weakness">${w}</div>`).join('')}
                    </div>
                </div>
            </div>
        </div>
    `;
}

function buildSkillsSegmentContent(m) {
    const matched = m.matched_skills;
    const missing = m.missing_skills;

    let html = '';

    if (matched.length > 0) {
        html += `<div class="segment-sub-label" style="color: hsl(152 40% 36%)">Matched (${matched.length})</div>`;
        html += '<div class="segment-chips">';
        html += matched.map(s =>
            `<div class="segment-chip matched" title="${s.evidence || s.candidate_skill}">
                <span>${s.required_skill}</span>
                <span class="chip-score">${Math.round(s.similarity * 100)}%</span>
            </div>`
        ).join('');
        html += '</div>';
    }

    if (missing.length > 0) {
        html += `<div class="segment-sub-label" style="color: hsl(0 45% 48%); margin-top: 12px;">Missing (${missing.length})</div>`;
        html += `<div class="segment-reason">These required skills were not found anywhere in the resume:</div>`;
        html += '<div class="segment-chips">';
        html += missing.map(s =>
            `<span class="segment-chip missing">${s}</span>`
        ).join('');
        html += '</div>';
    }

    if (!matched.length && !missing.length) {
        html = '<div class="empty-state">No skill data available</div>';
    }

    return html;
}

function buildExperienceSegmentContent(m, r) {
    let html = '';

    // Show experience entries
    if (r.experience.length > 0) {
        html += r.experience.map(e => `
            <div class="segment-exp-item">
                <div class="segment-exp-header">
                    <strong>${e.title}</strong> at ${e.company}
                    <span class="segment-exp-date">${e.start_date || '?'} — ${e.end_date || '?'}</span>
                </div>
                <div class="segment-exp-desc">${e.description}</div>
            </div>
        `).join('');
    } else {
        html += '<div class="segment-reason">No work experience entries were found in the resume.</div>';
    }

    // Show relevant weaknesses for experience
    const expWeaknesses = m.weaknesses.filter(w =>
        /experience|year|role|position|seniority/i.test(w)
    );
    if (expWeaknesses.length > 0) {
        html += '<div class="segment-shortcoming-label">Why this score:</div>';
        html += expWeaknesses.map(w => `<div class="segment-shortcoming">${w}</div>`).join('');
    }

    return html;
}

function buildEducationSegmentContent(m, r) {
    let html = '';

    if (r.education.length > 0) {
        html += r.education.map(e => `
            <div class="segment-edu-item">
                <div class="segment-edu-degree">${e.degree}${e.field ? ` in ${e.field}` : ''}</div>
                <div class="segment-edu-institution">${e.institution}</div>
                ${e.year ? `<div class="segment-edu-year">Class of ${e.year}</div>` : ''}
            </div>
        `).join('');
    } else {
        html += '<div class="segment-reason">No education entries were found in the resume.</div>';
    }

    // Show relevant weaknesses for education
    const eduWeaknesses = m.weaknesses.filter(w =>
        /education|degree|bachelor|master|phd|university|college|field/i.test(w)
    );
    if (eduWeaknesses.length > 0) {
        html += '<div class="segment-shortcoming-label">Why this score:</div>';
        html += eduWeaknesses.map(w => `<div class="segment-shortcoming">${w}</div>`).join('');
    }

    return html;
}

function buildProjectsSegmentContent(m, r) {
    let html = '';

    if (r.projects.length > 0) {
        html += r.projects.map(p => `
            <div class="segment-project-item">
                <div class="segment-project-name">${p.name}</div>
                <div class="segment-project-desc">${p.description}</div>
                ${p.technologies.length ? `<div class="segment-project-tech">${p.technologies.map(t => `<span class="segment-chip neutral">${t}</span>`).join('')}</div>` : ''}
            </div>
        `).join('');
    } else {
        html += '<div class="segment-reason">No project entries were found in the resume.</div>';
    }

    // Show relevant weaknesses for projects
    const projWeaknesses = m.weaknesses.filter(w =>
        /project|portfolio|hands-on|practical/i.test(w)
    );
    if (projWeaknesses.length > 0) {
        html += '<div class="segment-shortcoming-label">Why this score:</div>';
        html += projWeaknesses.map(w => `<div class="segment-shortcoming">${w}</div>`).join('');
    }

    return html;
}

function renderScoreBar(label, score) {
    const color = scoreBarColor(score);
    return `
        <div class="score-bar-item">
            <div class="score-bar-label">
                <span>${label}</span>
                <span style="color: ${color}">${score}%</span>
            </div>
            <div class="score-bar-track">
                <div class="score-bar-fill" style="width: ${score}%; background: ${color}"></div>
            </div>
        </div>
    `;
}

// ─── Utilities ──────────────────────────────────────────────────────────────

function formatSize(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// ─── Boot ───────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', init);
