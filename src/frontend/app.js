class Controller {
    constructor() {
        this.panels = document.querySelectorAll('.panel');
        this.fileInput = document.getElementById('fileInput');
        this.patientStream = null;
        this.clinicianStream = null;
        this.retrievalMode = document.getElementById('retrievalMode');
        this.speakerFilter = document.getElementById('speakerFilter');
        this.retrievalQuery = document.getElementById('retrievalQuery');
        this.queryRow = document.getElementById('queryRow');
        this.retrievalOutput = document.getElementById('retrievalOutput');
    }

    showPanel(id, navEl) {
        this.panels.forEach(p => {
            p.classList.remove('active');
            p.setAttribute('aria-hidden', 'true');
        });
        const panel = document.getElementById(id);
        if (panel) {
            panel.classList.add('active');
            panel.setAttribute('aria-hidden', 'false');
        }
        document.querySelectorAll('.sidebar .sidebar-item').forEach(el => {
            const on = el === navEl;
            el.classList.toggle('is-active', on);
            if (on) el.setAttribute('aria-current', 'page');
            else el.removeAttribute('aria-current');
        });
    }

    async assignAudioDevice(role){
        const existingLabel = document.getElementById(role === 'patient' ? 'patientAudio' : 'clinicianAudio');
        const assignButton = event.target

        try{
            //Stop Existing Stream
            if(role === 'patient' && this.patientStream){
                this.patientStream.getTracks().forEach(t => t.stop());
            } else if (role == 'clinician' && this.clinicianStream) {
                this.clinicianStream.getTracks().forEach(t => t.stop());
            }

            //Popup For Access
            const stream = await navigator.mediaDevices.getUserMedia({audio: true});
            const track = stream.getAudioTracks()[0];
            const name = track.label

            if(role === 'patient'){
                this.patientStream = stream;
            } else {
                this.clinicianStream = stream;
            }

            existingLabel.textContent = name;
            assignButton.classList.add('assigned');

        } catch (error) {
            alert(`Failed: ${error.message}`)
        }
    }

    async startLiveAudio() {
        const existingStatus = document.getElementById('streamStatus')
        
        if (!this.patientStream || !this.clinicianStream){
            alert('Please Assign Both Roles Audio')
        } else if (document.getElementById('patientAudio').textContent ===
                   document.getElementById('clinicianAudio').textContent) {
            alert('Audio Sources Identical: Please Choose Seperate Sources')
        } else {

            //LIVEKIT CONNECTING
            document.getElementById('streamStatus').textContent = 'Running'
        }
    }

    async stopLiveAudio(){

        //LIVEKIT STOPPING
        document.getElementById('streamStatus').textContent = 'Not Running';
    }

    async uploadAudioFile() {
        const file = this.fileInput.files[0];
        if (!file) {
            alert('No Audio File Selected');
            return;
        } else if (this.isProcessing){
            alert('Upload Already In Process');
            return;
        } else {
            //Caching Audio File
            const formData = new FormData();
            formData.append('audio', file);

            this.isProcessing = true;

            //Initiating N8N Flow
            try {
                alert("Starting Flow");
                const response = await fetch("http://localhost:5678/webhook/upload-audio", {
                    method: "POST",
                    body: formData
                });
                const data = await response.text();
                alert('N8N Output: ' + JSON.stringify(data))
            } catch(error) {
                alert('Error Uploading File: ' + error);
            } finally {
                this.isProcessing = false
            }
        }
    }

    //update retrievalQuery textarea placeholder
    updateRetrievalUI() {
        const mode = this.retrievalMode.value;

        if (mode === 'qa') {
            this.queryRow.style.display = 'block';
            this.retrievalQuery.placeholder = 'Enter a question: e.g. What symptoms did the patient report?';
        } else if (mode === 'summary') {
            this.queryRow.style.display = 'block';
            this.retrievalQuery.placeholder = 'Prompt not applicable for summary mode.';
        } else if (mode === 'analysis') {
            this.queryRow.style.display = 'block';
            this.retrievalQuery.placeholder = 'Prompt not applicable for analysis mode.';
        }
    }

    //get endpoints for each mode
    getRetrievalEndpoint(mode) {
        if (mode === 'summary') return 'http://localhost:8000/generate-summary';
        if (mode === 'analysis') return 'http://localhost:8000/generate-analysis';
        if (mode === 'qa') return 'http://localhost:8000/generate-answer';
        return null;
    }

    async prepareRetrievalRequest() {
        const mode = this.retrievalMode.value;
        const speaker = this.speakerFilter.value;
        const query = this.retrievalQuery.value.trim();

        let selectedModeLabel = '';
        if (mode === 'summary') selectedModeLabel = 'Clinical Interview Summarization';
        if (mode === 'analysis') selectedModeLabel = 'Automated Interview Analyzer';
        if (mode === 'qa') selectedModeLabel = 'Symptom-Based Question Answering';

        let endpoint = this.getRetrievalEndpoint(mode);

        //question/prompt is needed for qa mode
        if (mode === 'qa' && !query) {
            this.retrievalOutput.innerHTML = `
                <strong>Selected Mode:</strong> ${selectedModeLabel}<br>
                <strong>Speaker Filter:</strong> ${speaker}<br>
                <strong>Error:</strong> Please enter a question for Question Answering mode.
            `;
            return;
        }

        //send prompt to backend for qa
        if (mode === 'qa') {
            endpoint += `?query=${encodeURIComponent(query)}`;
        }

        //format output
        this.retrievalOutput.innerHTML = `
            <strong>Selected Mode:</strong> ${selectedModeLabel}<br>
            <strong>Speaker Filter:</strong> ${speaker}<br>
            <strong>Question / Prompt:</strong> ${query ? query : 'None entered'}<br><br>
            <em>Running retrieval...</em>
        `;

        try {
            const response = await fetch(endpoint, {
                method: 'POST'
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            let formattedResult = '';

            if (typeof data === 'string') {
                formattedResult = data;
            } else if (data.result) {
                formattedResult = data.result;
            } else if (data.response) {
                formattedResult = data.response;
            } else if (data.output) {
                formattedResult = data.output;
            } else {
                formattedResult = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
            }
        
            this.retrievalOutput.innerHTML = `
                <strong>Selected Mode:</strong> ${selectedModeLabel}<br>
                <strong>Speaker Filter:</strong> ${speaker}<br>
                <strong>Question / Prompt:</strong> ${query ? query : 'None entered'}<br><br>
                <strong>Backend Output:</strong><br>
                <div style="margin-top:8px; white-space:pre-wrap;">${formattedResult.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')}</div>
            `;
        } catch (error) {
            this.retrievalOutput.innerHTML = `
                <strong>Selected Mode:</strong> ${selectedModeLabel}<br>
                <strong>Speaker Filter:</strong> ${speaker}<br>
                <strong>Question / Prompt:</strong> ${query ? query : 'None entered'}<br><br>
                <strong>Error:</strong> ${error.message}
            `;
        }
    }


    clearRetrievalOutput() {
        this.retrievalOutput.innerHTML = 'Retrieval output will appear here.';
        this.retrievalQuery.value = '';
    }


    async evaluationModules(){

    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.controller = new Controller();
    window.controller.updateRetrievalUI();
    const firstNav = document.querySelector('.sidebar .sidebar-item.is-active');
    if (firstNav && firstNav.dataset.panel) {
        window.controller.showPanel(firstNav.dataset.panel, firstNav);
    }
});