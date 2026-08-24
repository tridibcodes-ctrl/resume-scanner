/**
 * API client for communicating with the Resume Screener backend.
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class ApiClient {
    constructor(baseUrl = API_BASE) {
        this.baseUrl = baseUrl.replace(/\/$/, '');
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const res = await fetch(url, {
            ...options,
            headers: {
                ...options.headers,
            },
        });

        if (!res.ok) {
            const error = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(error.detail || `API error: ${res.status}`);
        }

        return res.json();
    }

    /** Check backend health and LLM provider status. */
    async health() {
        return this.request('/api/health');
    }

    /** Create a new analysis session. */
    async createSession() {
        return this.request('/api/session', { method: 'POST' });
    }

    /** Upload resume files to a session. */
    async uploadResumes(sessionId, files) {
        const formData = new FormData();
        for (const file of files) {
            formData.append('files', file);
        }
        return this.request(`/api/session/${sessionId}/resumes`, {
            method: 'POST',
            body: formData,
        });
    }

    /** Submit job description text. */
    async submitJobDescription(sessionId, text) {
        return this.request(`/api/session/${sessionId}/job-description`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text }),
        });
    }

    /** Trigger the analysis pipeline. */
    async analyze(sessionId, similarityScores = null) {
        const body = {};
        if (similarityScores) {
            body.similarity_scores = similarityScores;
        }
        return this.request(`/api/session/${sessionId}/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
    }

    /** Get ranked results for a session. */
    async getResults(sessionId) {
        return this.request(`/api/session/${sessionId}/results`);
    }
}

export const api = new ApiClient();
