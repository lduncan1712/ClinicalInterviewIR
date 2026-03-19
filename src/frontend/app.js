class Controller {
    constructor() {
        this.panels = document.querySelectorAll('.panel');
        this.fileInput = document.getElementById('fileInput');
        this.patientStream = null;
        this.clinicianStream = null;
    }

    showPanel(id) {
        this.panels.forEach(p => p.classList.remove('active'));
        const panel = document.getElementById(id);
        if (panel) panel.classList.add('active');
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

    async retrievalModule_1(){

    }

    async retrievalModule_2(){

    }

    async retrievalModule_3(){

    }


    async evaluationModules(){

    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.controller = new Controller();
});