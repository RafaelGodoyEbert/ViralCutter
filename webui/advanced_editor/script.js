// static/script.js
const PIXELS_PER_SECOND = 100;
const WORD_ZOOM_THRESHOLD = 2.5; // Nível de zoom para mostrar palavras
const CHAR_ZOOM_THRESHOLD = 20; // Nível de zoom BEM ALTO para mostrar caracteres

document.addEventListener('DOMContentLoaded', () => {
    // GitHub Pages pode bloquear localStorage em iframes; preferimos manter o editor funcional.
    const safeStorage = {
        getItem(key, fallback = null) {
            try { return window.localStorage?.getItem(key) ?? fallback; } catch { return fallback; }
        },
        setItem(key, value) {
            try { window.localStorage?.setItem(key, String(value)); } catch {}
        }
    };

    // --- Referências ao DOM ---
    const app = document.querySelector('.app');
    const importJsonBtn = document.getElementById('import-json');
    const importMediaBtn = document.getElementById('import-media');
    const importYouTubeBtn = document.getElementById('import-youtube-btn');
    const mediaFileName = document.getElementById('media-file-name');
    const addSubtitleBtn = document.getElementById('add-subtitle');
    const saveJsonBtn = document.getElementById('save-json');
    const saveProjectBtn = document.getElementById('save-project');
    const faithfulPreviewBtn = document.getElementById('faithful-preview');
    const playPauseBtn = document.getElementById('play-pause');
    const shuttleReverseBtn = document.getElementById('shuttle-reverse');
    const shuttleForwardBtn = document.getElementById('shuttle-forward');
    const playbackSpeed = document.getElementById('playback-speed');
    const themeToggleBtn = document.getElementById('theme-toggle');
    const timelineFrame = document.getElementById('timeline-frame');
    const timelineContent = document.getElementById('timeline-content');
    const timelineRuler = document.getElementById('timeline-ruler');
    const timelineScrollContainer = document.getElementById('timeline-scroll-container');
    const cursor = document.getElementById('cursor');
    const mediaPlayer = document.getElementById('media-player');
    const videoPlaceholder = document.getElementById('video-placeholder');
    const subtitleOverlay = document.getElementById('subtitle-overlay');
    const previewArea = document.getElementById('preview-area');
    const contextMenu = document.getElementById('context-menu');
    const waveformCanvas = document.getElementById('waveform-canvas');
    const waveformCtx = waveformCanvas.getContext('2d');
    const autoGenerateCharsCheckbox = document.getElementById('auto-generate-chars');
    const deleteOnShortenCheckbox = document.getElementById('delete-on-shorten');
    const followPlaybackCheckbox = document.getElementById('follow-playback');
    const wordHighlightCheckbox = document.getElementById('word-highlight');
    const snapEnabledCheckbox = document.getElementById('snap-enabled');
    const snapKeyOnlyCheckbox = document.getElementById('snap-key-only');
    const snapGapMsInput = document.getElementById('snap-gap-ms');
    const snapVerticalGuide = document.getElementById('snap-vertical-guide');
    const videoCurrentTimecode = document.getElementById('video-current-timecode');
    const videoTotalTimecode = document.getElementById('video-total-timecode');
    const zoomIndicator = document.getElementById('zoom-indicator');
    const trackSelector = document.getElementById('track-selector');
    const addTrackBtn = document.getElementById('add-track');
    const mergePunctuationBtn = document.getElementById('merge-by-punctuation');
    const syncWaveformBtn = document.getElementById('sync-waveform-btn');
    const projectParams = new URLSearchParams(location.search);
    const projectName = projectParams.get('project');
    const projectFile = projectParams.get('file');
    const projectVideo = projectParams.get('video');
    let subtitleConfig = {};
    let useNativeVtt = false;
    let projectTrack = null;
    let subtitleConfigSignature = '';
    let projectVttUrl = null;
    let vttRefreshTimer = null;

    // Referências do Modal de Exportação
    const exportModal = document.getElementById('export-modal');
    const exportFormatSelect = document.getElementById('export-format');
    const exportTrackModeSelect = document.getElementById('export-track-mode');
    const confirmExportBtn = document.getElementById('confirm-export');
    const cancelExportBtn = document.getElementById('cancel-export');

    const resizerH = document.getElementById('resizer-h');
    const resizerV = document.getElementById('resizer-v');
    const workspace = document.getElementById('workspace');
    const editorPane = document.getElementById('editor-pane');
    const toggleLayoutBtn = document.getElementById('toggle-layout');
    const videoPreview = document.getElementById('video-preview');
    const languageSelector = document.getElementById('language-selector');
    const splitPunctuationBtn = document.getElementById('split-by-punctuation');

    // Referências do Modal de Busca/Substituição
    const findModal = document.getElementById('find-modal');
    const findInput = document.getElementById('find-input');
    const findNextBtn = document.getElementById('find-next-btn');
    const findPreviousBtn = document.getElementById('find-previous-btn');
    const findStatus = document.getElementById('find-status');
    const closeFindBtn = document.getElementById('close-find');

    const replaceModal = document.getElementById('replace-modal');
    const replaceFindInput = document.getElementById('replace-find-input');
    const replaceWithInput = document.getElementById('replace-with-input');
    const replaceNextBtn = document.getElementById('replace-next-btn');
    const replacePreviousBtn = document.getElementById('replace-previous-btn');
    const replaceOneBtn = document.getElementById('replace-one-btn');
    const replaceAllBtn = document.getElementById('replace-all-btn');
    const replaceStatus = document.getElementById('replace-status');
    const closeReplaceBtn = document.getElementById('close-replace');

    // Referências Menu Mobile
    const mobileMenuBtn = document.getElementById('mobile-menu-btn');
    const mainControls = document.getElementById('main-controls');

    if (mobileMenuBtn && mainControls) {
        mobileMenuBtn.addEventListener('click', () => {
            mainControls.classList.toggle('open');
        });
    }

    // --- Helpers de Touch/Mouse ---
    function getClientX(e) { return e.touches && e.touches.length > 0 ? e.touches[0].clientX : e.clientX; }
    function getClientY(e) { return e.touches && e.touches.length > 0 ? e.touches[0].clientY : e.clientY; }

    // --- Estado da Aplicação ---
    let state = {
        subtitles: [],
        selectedSubtitles: [],
        history: [],
        historyIndex: -1,
        copiedSubtitles: [],
        zoomLevel: 1,
        cursorPosition: 0,
        isPlaying: false,
        playbackDirection: 1,
        playbackRate: 1,
        mediaUrl: null,
        mediaDuration: 0,
        lastSelected: null,
        isDraggingCursor: false,
        lastAdjustRequest: null,
        waveformData: null,
        audioDuration: 0,
        autoGenerateChars: true,
        deleteOnShorten: safeStorage.getItem('subtitle_editor:delete_on_shorten') === 'true',
        followPlayback: safeStorage.getItem('subtitle_editor:follow_playback') !== 'false',
        wordHighlight: safeStorage.getItem('subtitle_editor:word_highlight') !== 'false',
        snapEnabled: safeStorage.getItem('subtitle_editor:snap_enabled') !== 'false',
        snapKeyOnly: safeStorage.getItem('subtitle_editor:snap_key_only') !== 'false',
        snapGapMs: Number(safeStorage.getItem('subtitle_editor:snap_gap_ms', 50)) || 50,
        lastActiveSubId: null,
        tracks: ['Track 1'],
        activeTrack: 'Track 1',
        hiddenTracks: [], // Trilhas ocultas no preview
        language: 'pt-br',
        subtitleSearch: ''
    };

    // --- Internacionalização (i18n) ---
    let translations = {};
    let ytPlayer = null;
    let ytReady = false;
    let ytVideoId = null;

    async function initI18n() {
        // 1. Tenta carregar da variável global (languages.js) - Funciona localmente sem server
        if (typeof I18N_DATA !== 'undefined') {
            translations = I18N_DATA;
            console.log('Traduções carregadas via languages.js (Global)');
        } else {
            // 2. Fallback: tenta fetch no JSON (caso use servidor)
            try {
                const response = await fetch('languages.json');
                if (response.ok) {
                    translations = await response.json();
                }
            } catch (error) {
                console.warn('Não foi possível carregar traduções.', error);
            }
        }

        // Popula o seletor de idiomas dinamicamente
        if (languageSelector) {
            languageSelector.innerHTML = ''; // Limpa opções existentes
            Object.keys(translations).forEach(lang => {
                const option = document.createElement('option');
                option.value = lang;
                option.textContent = lang.toUpperCase();
                languageSelector.appendChild(option);
            });
        }

        // Tenta detectar o idioma do navegador ou usa o padrão
        const browserLang = navigator.language.toLowerCase();
        let defaultLang = 'en';

        // Verifica se temos tradução para a lingua exata ou só para o prefixo (pt-br vs pt)
        if (translations[browserLang]) defaultLang = browserLang;
        else if (translations[browserLang.split('-')[0]]) defaultLang = browserLang.split('-')[0];
        else if (translations['pt-br']) defaultLang = 'pt-br'; // Preferência por PT-BR se disponível

        // Garante que o idioma selecionado existe nas traduções, senão usa o primeiro disponível
        if (!translations[defaultLang]) {
            defaultLang = Object.keys(translations)[0];
        }

        updateState({ language: defaultLang });
        if (languageSelector) languageSelector.value = defaultLang;

        applyTranslations();
    }

    function t(key) {
        if (translations[state.language] && translations[state.language][key]) {
            return translations[state.language][key];
        }
        // Fallback para inglês se não houver na lingua selecionada
        if (translations['en'] && translations['en'][key]) {
            return translations['en'][key];
        }
        return key;
    }

    function applyTranslations() {
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            el.textContent = t(key);
        });
        document.querySelectorAll('[data-i18n-title]').forEach(el => {
            const key = el.getAttribute('data-i18n-title');
            el.title = t(key);
        });
        document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
            const key = el.getAttribute('data-i18n-placeholder');
            el.placeholder = t(key);
        });

        updateIndicators();
    }

    function updateIndicators() {
        // Atualiza indicadores dinâmicos
        if (zoomIndicator) {
            zoomIndicator.innerHTML = `<span data-i18n="zoom">${t('zoom')}</span>: ${state.zoomLevel.toFixed(1)}x`;
        }

        if (toggleLayoutBtn) {
            const is916 = workspace.classList.contains('layout-916');
            toggleLayoutBtn.textContent = is916 ? t('mode_169') : t('mode_916');
        }
    }

    // --- Funções de Atualização de Estado e Renderização ---

    function updateState(newState) {
        // Debug: rastreia mudanças no waveformData
        if ('waveformData' in newState && newState.waveformData !== state.waveformData) {
            console.log('[State] waveformData mudou:', {
                antes: state.waveformData ? state.waveformData.length + ' peaks' : 'null',
                depois: newState.waveformData ? newState.waveformData.length + ' peaks' : 'null',
                zoom: state.zoomLevel
            });
        }

        Object.assign(state, newState);

        // Atualiza indicadores e traduções se a linguagem mudar
        if (newState.language) {
            applyTranslations();
        } else {
            updateIndicators();
        }

        // Atualiza seletor de tracks se necessário
        if (newState.tracks || newState.activeTrack || newState.hiddenTracks) {
            renderTrackSelector();
        }
    }

    function recordHistory() {
        const newHistory = state.history.slice(0, state.historyIndex + 1);
        newHistory.push(JSON.parse(JSON.stringify(state.subtitles))); // Deep copy
        updateState({ history: newHistory, historyIndex: newHistory.length - 1 });
    }

    function updateSubtitles(newSubs, record = true) {
        updateState({ subtitles: newSubs });
        if (record) {
            recordHistory();
        }
        renderTimeline();
        renderPreviewArea();
        if (useNativeVtt) scheduleProjectTrackRefresh();
    }

    function renderTrackSelector() {
        if (!trackSelector) return;
        trackSelector.innerHTML = '';
        state.tracks.forEach(track => {
            const option = document.createElement('option');
            option.value = track;
            option.textContent = track;
            option.selected = (track === state.activeTrack);
            trackSelector.appendChild(option);
        });
    }



    // --- Lógica de Renderização ---

    function generateId() {
        return Date.now() + Math.random().toString(36).substr(2, 9);
    }

    // Gera caracteres automaticamente a partir das palavras
    function generateCharsFromWords(subtitle) {
        // Lista de pontuações que devem receber menos tempo
        const punctuationChars = '.,;:!?¡¿‽⁇⁈⁉…-–—―()[]{}«»""\'\'`´';
        if (!subtitle.words || subtitle.words.length === 0) {
            // Se não tem words, gera chars do texto uniformemente
            const chars = [];
            const text = subtitle.text || '';
            const duration = subtitle.end - subtitle.start;

            // Calcula pesos: pontuação = 0.05, letras/números/espaços = 1.0
            const weights = [];
            let totalWeight = 0;
            for (let i = 0; i < text.length; i++) {
                const char = text[i];
                const isPunctuation = punctuationChars.includes(char);
                const weight = isPunctuation ? 0.05 : 1.0;
                weights.push(weight);
                totalWeight += weight;
            }

            let currentTime = subtitle.start;
            for (let i = 0; i < text.length; i++) {
                const charDuration = (weights[i] / totalWeight) * duration;
                chars.push({
                    char: text[i],
                    start: currentTime,
                    end: currentTime + charDuration
                });
                currentTime += charDuration;
            }
            return chars;
        }

        // Gera chars a partir das palavras
        const chars = [];
        subtitle.words.forEach(word => {
            const wordText = word.word || '';
            const wordDuration = word.end - word.start;

            // Calcula pesos para cada caractere da palavra
            const weights = [];
            let totalWeight = 0;
            for (let i = 0; i < wordText.length; i++) {
                const char = wordText[i];
                const isPunctuation = punctuationChars.includes(char);
                const weight = isPunctuation ? 0.05 : 1.0;
                weights.push(weight);
                totalWeight += weight;
            }

            let currentTime = word.start;
            for (let i = 0; i < wordText.length; i++) {
                const charDuration = (weights[i] / totalWeight) * wordDuration;
                chars.push({
                    char: wordText[i],
                    start: currentTime,
                    end: currentTime + charDuration
                });
                currentTime += charDuration;
            }
        });

        return chars;
    }

    function renderTimeline() {
        // Limpa a timeline
        timelineContent.innerHTML = '';
        timelineContent.appendChild(cursor);

        const totalDuration = Math.max(
            ...state.subtitles.map(s => s.end), state.mediaDuration || 0, state.audioDuration || 0, 10
        ) + 10;
        const totalTracks = state.tracks.length;
        const rowHeight = 60; // Altura de cada "camada"

        timelineFrame.style.width = `${totalDuration * PIXELS_PER_SECOND * state.zoomLevel}px`;
        timelineFrame.style.height = `${75 + totalTracks * rowHeight}px`; // Ajusta altura total
        timelineContent.style.height = `${totalTracks * rowHeight}px`;

        // Renderiza fundos das camadas
        state.tracks.forEach((track, i) => {
            const isHidden = state.hiddenTracks.includes(track);
            const trackBg = document.createElement('div');
            trackBg.className = 'track-bg';
            if (track === state.activeTrack) {
                trackBg.classList.add('active');
            }
            // Não aplica mais opacity - hidden afeta APENAS o preview
            trackBg.style.top = `${i * rowHeight}px`;
            trackBg.style.height = `${rowHeight}px`;
            trackBg.style.pointerEvents = 'auto'; // Permite clique

            // Toggle de camada ao clicar no fundo
            trackBg.addEventListener('click', (e) => {
                // Impede que o clique no fundo mude o cursor de tempo (seek)
                e.stopPropagation();
                updateState({ activeTrack: track });
                renderTimeline();
            });

            const trackLabel = document.createElement('div');
            trackLabel.className = 'track-label-container';
            trackLabel.style.display = 'flex';
            trackLabel.style.alignItems = 'center';
            trackLabel.style.gap = '8px';
            trackLabel.style.padding = '4px 8px';
            trackLabel.style.position = 'absolute'; // Muda para absolute
            trackLabel.style.left = '0'; // Será atualizado pelo scroll
            trackLabel.style.top = '0';
            trackLabel.style.zIndex = '1000';
            trackLabel.style.background = '#2f3136';
            trackLabel.style.boxShadow = '2px 0 4px rgba(0,0,0,0.3)';
            trackLabel.style.width = 'fit-content';
            trackLabel.style.pointerEvents = 'none';
            trackLabel.dataset.trackLabel = 'true'; // Marca para atualizar no scroll

            const visibilityBtn = document.createElement('span');
            visibilityBtn.innerHTML = isHidden ? '❌' : '👁️';
            visibilityBtn.style.cursor = 'pointer';
            visibilityBtn.style.pointerEvents = 'auto'; // Reativa cliques no botão
            visibilityBtn.title = isHidden ? 'Mostrar no preview' : 'Ocultar no preview';
            visibilityBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                let newHidden = [...state.hiddenTracks];
                if (isHidden) {
                    newHidden = newHidden.filter(t => t !== track);
                } else {
                    newHidden.push(track);
                }
                updateState({ hiddenTracks: newHidden });
                renderTimeline();
                renderCursor();
            });

            const textLabel = document.createElement('span');
            textLabel.className = 'track-label';
            textLabel.textContent = track;
            textLabel.style.pointerEvents = 'auto'; // Reativa cliques no texto

            trackLabel.appendChild(visibilityBtn);
            trackLabel.appendChild(textLabel);
            trackBg.appendChild(trackLabel);
            timelineContent.appendChild(trackBg);
        });

        // Renderiza legendas
        const selectedIds = new Set(state.selectedSubtitles.map(subtitle => subtitle.id));
        state.subtitles.forEach((sub, index) => {
            const block = document.createElement('div');
            block.className = 'subtitle-block';
            if (selectedIds.has(sub.id)) {
                block.classList.add('selected');
            }

            const trackIndex = state.tracks.indexOf(sub.track || state.tracks[0]);
            block.style.top = `${trackIndex * rowHeight + 10}px`; // 10px de margem interna
            block.style.left = `${sub.start * PIXELS_PER_SECOND * state.zoomLevel}px`;
            block.style.width = `${(sub.end - sub.start) * PIXELS_PER_SECOND * state.zoomLevel}px`;

            // Handles de redimensionamento do bloco
            const leftHandle = document.createElement('div');
            leftHandle.className = 'resize-handle left';
            leftHandle.addEventListener('mousedown', (e) => handleResizeStart(e, index, 'left'));
            leftHandle.addEventListener('touchstart', (e) => handleResizeStart(e, index, 'left'), { passive: false });

            const rightHandle = document.createElement('div');
            rightHandle.className = 'resize-handle right';
            rightHandle.addEventListener('mousedown', (e) => handleResizeStart(e, index, 'right'));
            rightHandle.addEventListener('touchstart', (e) => handleResizeStart(e, index, 'right'), { passive: false });

            // Área de arrastar que conterá a visualização apropriada
            const dragArea = document.createElement('div');
            dragArea.className = 'drag-area';
            dragArea.addEventListener('pointerdown', (e) => {
                const wordEl = e.target.closest('.word');
                if (wordEl && !e.target.closest('.word-handle')) {
                    handleWordMoveStart(e, index, Number(wordEl.dataset.wordIndex));
                    return;
                }
                if (!e.target.closest('.word-handle') && !e.target.closest('.char-handle')) handleMoveStart(e, index);
            });

            // --- LÓGICA DE VISUALIZAÇÃO DE 3 NÍVEIS ---
            const showCharLevel = state.zoomLevel >= CHAR_ZOOM_THRESHOLD;
            const showWordLevel = state.zoomLevel >= WORD_ZOOM_THRESHOLD && sub.words && sub.words.length > 0;

            // Se deve mostrar chars mas não existem, gera automaticamente (se habilitado)
            let charsToShow = sub.chars;
            if (showCharLevel && state.autoGenerateChars && (!sub.chars || sub.chars.length === 0)) {
                charsToShow = generateCharsFromWords(sub);
            }

            if (showCharLevel && charsToShow && charsToShow.length > 0) {
                // NÍVEL 3: CARACTERES
                const charContainer = document.createElement('div');
                charContainer.className = 'char-container';

                charsToShow.forEach((char, charIdx) => {
                    if (char.start === undefined || char.end === undefined) return; // Ignora caracteres sem tempo

                    const charEl = document.createElement('div');
                    charEl.className = 'char';
                    charEl.textContent = char.char;

                    const charWidth = (char.end - char.start) * PIXELS_PER_SECOND * state.zoomLevel;
                    charEl.style.width = `${charWidth}px`;

                    // Adiciona handle entre caracteres
                    if (charIdx < charsToShow.length - 1) {
                        const nextChar = charsToShow[charIdx + 1];
                        if (nextChar.start !== undefined && nextChar.end !== undefined) {
                            const charHandle = document.createElement('div');
                            charHandle.className = 'char-handle';
                            charHandle.addEventListener('mousedown', (e) => handleCharResizeStart(e, index, charIdx));
                            charHandle.addEventListener('touchstart', (e) => handleCharResizeStart(e, index, charIdx), { passive: false });
                            charEl.appendChild(charHandle);
                        }
                    }
                    charContainer.appendChild(charEl);
                });
                dragArea.appendChild(charContainer);
            } else if (showWordLevel) {
                // NÍVEL 2: PALAVRAS
                const wordContainer = document.createElement('div');
                wordContainer.className = 'word-container';
                dragArea.style.padding = '0';

                const wordsToShow = sub.words;

                wordsToShow.forEach((word, wordIdx) => {
                    const wordEl = document.createElement('div');
                    wordEl.className = 'word';
                    wordEl.dataset.wordIndex = wordIdx;

                    let wStart = word.start;
                    let wEnd = word.end;

                    if (wStart === undefined || wEnd === undefined) {
                        const sStart = sub.start;
                        const sEnd = sub.end;
                        const subDuration = sEnd - sStart;
                        wStart = sStart + (subDuration / wordsToShow.length) * wordIdx;
                        wEnd = sStart + (subDuration / wordsToShow.length) * (wordIdx + 1);
                    }

                    wordEl.style.left = `${(wStart - sub.start) * PIXELS_PER_SECOND * state.zoomLevel}px`;
                    wordEl.style.width = `${(wEnd - wStart) * PIXELS_PER_SECOND * state.zoomLevel}px`;
                    wordEl.textContent = word.word;

                    // Adiciona a classe de busca se aplicável
                    if (typeof searchResults !== 'undefined' && currentSearchIndex >= 0 && searchResults.length > 0) {
                        const isMatch = searchResults.some(res =>
                            res.subtitle.id === sub.id &&
                            res.type === 'word' &&
                            res.index === wordIdx
                        );
                        if (isMatch) wordEl.classList.add('search-highlight-word');
                    }

                    wordContainer.appendChild(wordEl);

                    // Só adiciona a alça (resizer) caso seja adjacente perfeitamente à próxima palavra, 
                    // ou simplesmente se houver palavra seguinte, podemos permitir o redimensionamento.
                    if (wordIdx < wordsToShow.length - 1) {
                        const wordHandle = document.createElement('div');
                        wordHandle.className = 'word-handle';
                        wordHandle.addEventListener('mousedown', (e) => handleWordResizeStart(e, index, wordIdx));
                        wordHandle.addEventListener('touchstart', (e) => handleWordResizeStart(e, index, wordIdx), { passive: false });
                        wordEl.appendChild(wordHandle);
                    }
                });
                dragArea.appendChild(wordContainer);
            } else {
                // NÍVEL 1: TEXTO COMPLETO
                const plainText = document.createElement('div');
                plainText.className = 'plain-text';
                plainText.textContent = sub.text;
                dragArea.appendChild(plainText);
            }

            block.appendChild(leftHandle);
            block.appendChild(dragArea);
            block.appendChild(rightHandle);

            block.addEventListener('click', (e) => handleSelectSubtitle(e, sub));
            block.addEventListener('contextmenu', (e) => handleContextMenu(e, sub));

            // Touch handlers para mobile: tap para selecionar, long press para context menu
            let pressTimer;
            let touchStartTime = 0;
            let touchStartPos = { x: 0, y: 0 };
            let touchMoved = false;
            block.addEventListener('touchstart', (e) => {
                touchStartTime = Date.now();
                touchStartPos = { x: e.touches[0].clientX, y: e.touches[0].clientY };
                touchMoved = false;
                pressTimer = setTimeout(() => {
                    handleContextMenu(e, sub);
                }, 500);
            }, { passive: true });
            block.addEventListener('touchmove', (e) => {
                const dx = e.touches[0].clientX - touchStartPos.x;
                const dy = e.touches[0].clientY - touchStartPos.y;
                if (Math.abs(dx) > 10 || Math.abs(dy) > 10) {
                    touchMoved = true;
                    clearTimeout(pressTimer);
                }
            }, { passive: true });
            block.addEventListener('touchend', (e) => {
                clearTimeout(pressTimer);
                const elapsed = Date.now() - touchStartTime;
                // Tap rápido sem mover = selecionar
                if (!touchMoved && elapsed < 300) {
                    e.preventDefault();
                    handleSelectSubtitle(e, sub);
                }
            });

            timelineContent.appendChild(block);
        });

        renderRuler(totalDuration);
        renderWaveform();

        // Atualiza posição dos labels de track baseado no scroll atual
        const scrollLeft = timelineScrollContainer.scrollLeft;
        document.querySelectorAll('[data-track-label="true"]').forEach(label => {
            label.style.left = `${scrollLeft}px`;
        });
    }

    function renderRuler(duration) {
        timelineRuler.innerHTML = '';
        for (let i = 0; i <= duration; i += 1) {
            const marker = document.createElement('div');
            marker.className = 'time-marker';
            marker.style.left = `${i * PIXELS_PER_SECOND * state.zoomLevel}px`;
            marker.textContent = `${i}s`;
            timelineRuler.appendChild(marker);
        }
    }

    function escapeHtml(value) {
        return String(value || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    async function loadProjectSubtitles() {
        if (!projectName || !projectFile) return;
        try {
            importJsonBtn.hidden = true;
            importMediaBtn.closest('.media-picker').hidden = true;
            importYouTubeBtn.hidden = true;
            wordHighlightCheckbox.checked = true;
            updateState({ wordHighlight: true });
            if (projectVideo) {
                workspace.classList.add('layout-916');
                workspace.style.gridTemplateColumns = '1fr 350px';
                workspace.style.gridTemplateRows = '55% 1fr';
                resizerH.style.left = 'calc(100% - 350px)';
                resizerH.style.height = '100%';
                resizerV.style.top = '55%';
                updateIndicators();
                loadVideoLink(new URL(projectVideo, location.origin).href);
                projectTrack = document.createElement('track');
                projectTrack.kind = 'subtitles';
                projectTrack.default = true;
                projectTrack.src = `api/subtitles.vtt?project=${encodeURIComponent(projectName)}&file=${encodeURIComponent(projectFile)}`;
                mediaPlayer.replaceChildren(projectTrack);
                useNativeVtt = true;
                mediaPlayer.load();
                subtitleOverlay.style.display = 'none';
            }
            const configResponse = await fetch('api/subtitle-config', { cache: 'no-store' });
            if (configResponse.ok) applySubtitleConfig(await configResponse.json());
            setInterval(async () => { const response = await fetch('api/subtitle-config', { cache: 'no-store' }); if (response.ok) applySubtitleConfig(await response.json()); }, 1000);
            const response = await fetch(`api/subtitles?project=${encodeURIComponent(projectName)}&file=${encodeURIComponent(projectFile)}`);
            const json = await response.json();
            if (!response.ok || json.error) throw new Error(json.error || 'Falha ao carregar legendas.');
            updateSubtitles((json.segments || []).map((segment, index) => ({
                ...segment, id: generateId() + '_project_' + index, track: state.activeTrack
            })));
            saveProjectBtn.hidden = false;
            faithfulPreviewBtn.hidden = false;
        } catch (error) {
            alert(`Não foi possível carregar as legendas: ${error.message}`);
        }
    }

    saveProjectBtn.addEventListener('click', async () => {
        const segments = state.subtitles.map(({ id, track, ...segment }) => segment);
        try {
            const response = await fetch(`api/subtitles?project=${encodeURIComponent(projectName)}&file=${encodeURIComponent(projectFile)}`, {
                method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ segments })
            });
            const result = await response.json();
            if (!response.ok || result.error) throw new Error(result.error || 'Falha ao salvar legendas.');
            refreshProjectTrack();
            alert('Legendas salvas no projeto.');
        } catch (error) {
            alert(`Não foi possível salvar as legendas: ${error.message}`);
        }
    });

    faithfulPreviewBtn?.addEventListener('click', async () => {
        if (!projectName || !projectFile || !projectVideo) return;
        const previewWindow = window.open('', '_blank');
        const originalLabel = faithfulPreviewBtn.textContent;
        faithfulPreviewBtn.disabled = true;
        faithfulPreviewBtn.textContent = '⏳ Renderizando prévia…';
        try {
            const segments = state.subtitles.map(({ id, track, ...segment }) => segment);
            const response = await fetch(`api/faithful-preview?project=${encodeURIComponent(projectName)}&file=${encodeURIComponent(projectFile)}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ time: state.cursorPosition, segments })
            });
            const result = await response.json();
            if (!response.ok || result.error) throw new Error(result.error || 'Falha ao renderizar a prévia.');
            const url = new URL(result.url, location.origin).href;
            if (previewWindow) previewWindow.location = url;
            else window.open(url, '_blank');
        } catch (error) {
            previewWindow?.close();
            alert(`Não foi possível gerar a prévia fiel: ${error.message}`);
        } finally {
            faithfulPreviewBtn.disabled = false;
            faithfulPreviewBtn.textContent = originalLabel;
        }
    });

    function getSubtitleWords(subtitle) {
        if (subtitle?.words?.length) return subtitle.words;
        const tokens = String(subtitle?.text || '').trim().split(/\s+/).filter(Boolean);
        const duration = Math.max(.1, subtitle.end - subtitle.start);
        return tokens.map((word, index) => ({
            word,
            start: subtitle.start + index * duration / tokens.length,
            end: subtitle.start + (index + 1) * duration / tokens.length
        }));
    }

    function updateFollowAndWordHighlight() {
        const activeSub = state.subtitles.find(subtitle => {
            const track = subtitle.track || state.tracks[0];
            return state.cursorPosition >= subtitle.start && state.cursorPosition <= subtitle.end && !state.hiddenTracks.includes(track);
        });
        const previousId = state.lastActiveSubId;
        state.lastActiveSubId = activeSub?.id ?? null;
        previewArea.querySelectorAll('.subtitle-list-row.active-playback').forEach(row => row.classList.remove('active-playback'));
        if (previousId && previousId !== activeSub?.id) {
            previewArea.querySelector(`.subtitle-list-row[data-sub-id="${CSS.escape(String(previousId))}"]`)?._renderWordSpans?.();
        }
        if (!activeSub) return;

        const row = previewArea.querySelector(`.subtitle-list-row[data-sub-id="${CSS.escape(String(activeSub.id))}"]`);
        if (!row) return;
        row.classList.add('active-playback');
        if (state.followPlayback && previousId !== activeSub.id && document.activeElement?.tagName !== 'TEXTAREA') {
            row.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
        if (state.wordHighlight) row._renderWordSpans?.();
    }

    function formatTimecode(seconds, fps = 30) {
        const safeSeconds = Math.max(0, Number(seconds) || 0);
        const totalFrames = Math.round(safeSeconds * fps);
        const frames = totalFrames % fps;
        const totalSeconds = Math.floor(totalFrames / fps);
        const secs = totalSeconds % 60;
        const mins = Math.floor(totalSeconds / 60) % 60;
        const hours = Math.floor(totalSeconds / 3600);
        return [hours, mins, secs, frames].map(value => String(value).padStart(2, '0')).join(':');
    }

    function updateTimecodeDisplays() {
        if (videoCurrentTimecode) videoCurrentTimecode.textContent = formatTimecode(state.cursorPosition);
        if (videoTotalTimecode) videoTotalTimecode.textContent = formatTimecode(state.mediaDuration);
    }

    function renderCursor() {
        cursor.style.left = `${state.cursorPosition * PIXELS_PER_SECOND * state.zoomLevel}px`;
        if (mediaPlayer.src) {
            const diff = Math.abs(mediaPlayer.currentTime - state.cursorPosition);
            if (diff > .1 || (!state.isPlaying && diff > .01)) mediaPlayer.currentTime = state.cursorPosition;
        }

        const activeSubs = state.subtitles.filter(subtitle => {
            const track = subtitle.track || 'Track 1';
            return state.cursorPosition >= subtitle.start && state.cursorPosition <= subtitle.end && !state.hiddenTracks.includes(track);
        });
        if (useNativeVtt) {
            subtitleOverlay.style.display = 'none';
        } else if (activeSubs.length) {
            subtitleOverlay.innerHTML = activeSubs.map(subtitle => {
                const words = getSubtitleWords(subtitle), active = words.findIndex(word => state.cursorPosition >= word.start && state.cursorPosition <= word.end), mode = subtitleConfig.mode || 'highlight', size = Number(subtitleConfig.words_per_block || 3);
                const shown = mode === 'word_by_word' ? (active >= 0 ? [words[active]] : []) : words.slice(Math.floor(Math.max(active, 0) / size) * size, Math.floor(Math.max(active, 0) / size) * size + size);
                return shown.map(word => `<span class="overlay-word ${mode === 'highlight' && words.indexOf(word) === active ? 'word-active' : ''}" style="font-size:${mode === 'highlight' && words.indexOf(word) === active ? (subtitleConfig.highlight_size || subtitleConfig.base_size || 30) : (subtitleConfig.base_size || 30)}px">${escapeHtml(word.word)}</span>`).join(' ');
            }).join('<br>');
            subtitleOverlay.style.display = 'block';
        } else subtitleOverlay.style.display = 'none';
        updateFollowAndWordHighlight();
        updateTimecodeDisplays();
    }

    function renderPreviewArea() {
        previewArea.innerHTML = '';
        if (!state.subtitles.length) {
            previewArea.textContent = t('no_selection');
            return;
        }

        const searchBar = document.createElement('label');
        searchBar.className = 'subtitle-search';
        searchBar.innerHTML = '<span aria-hidden="true">🔍</span>';
        const searchInput = document.createElement('input');
        searchInput.type = 'search';
        searchInput.placeholder = 'Pesquisar legendas';
        searchInput.setAttribute('aria-label', 'Pesquisar legendas');
        searchInput.value = state.subtitleSearch;
        searchBar.appendChild(searchInput);
        previewArea.appendChild(searchBar);

        const selectedIds = new Set(state.selectedSubtitles.map(subtitle => subtitle.id));
        state.subtitles.forEach((subtitle, index) => {
            const row = document.createElement('div');
            row.className = `subtitle-list-row${selectedIds.has(subtitle.id) ? ' selected' : ''}`;
            row.dataset.subId = subtitle.id;
            row.dataset.search = `${index + 1} ${formatClock(subtitle.start)} ${formatClock(subtitle.end)} ${subtitle.text || ''}`.toLocaleLowerCase();
            row.hidden = !!state.subtitleSearch && !row.dataset.search.includes(state.subtitleSearch.toLocaleLowerCase());

            const number = document.createElement('span');
            number.className = 'subtitle-number';
            number.textContent = `${index + 1}.`;

            const times = document.createElement('span');
            times.className = 'subtitle-times';
            times.textContent = `${formatClock(subtitle.start)}\n${formatClock(subtitle.end)}`;
            times.title = 'Clique para posicionar a agulha no início';
            times.addEventListener('click', event => {
                event.stopPropagation();
                selectSubtitle();
                setCursorPosition(subtitle.start);
            });

            const cell = document.createElement('div');
            cell.className = 'subtitle-cell';
            const textarea = document.createElement('textarea');
            textarea.rows = Math.max(2, Math.ceil(String(subtitle.text || '').length / 58));
            textarea.value = subtitle.text || '';
            textarea.setAttribute('aria-label', `Legenda ${index + 1}`);
            const wordsContainer = document.createElement('div');
            wordsContainer.className = 'subtitle-words-container';
            const renderWordSpans = () => {
                const current = state.subtitles.find(item => item.id === subtitle.id) || subtitle;
                wordsContainer.replaceChildren();
                getSubtitleWords(current).forEach((word, wordIndex) => {
                    if (wordIndex) wordsContainer.append(' ');
                    const span = document.createElement('span');
                    span.className = 'word-token';
                    span.dataset.start = word.start;
                    span.dataset.end = word.end;
                    if (state.lastActiveSubId === current.id) {
                        if (state.cursorPosition >= word.start && state.cursorPosition <= word.end) span.classList.add('word-active');
                        else if (state.cursorPosition > word.end) span.classList.add('word-spoken');
                    }
                    span.textContent = word.word;
                    wordsContainer.append(span);
                });
            };
            row._renderWordSpans = renderWordSpans;
            renderWordSpans();
            const selectSubtitle = () => {
                const current = state.subtitles.find(item => item.id === subtitle.id) || subtitle;
                updateState({ selectedSubtitles: [current], lastSelected: current });
                previewArea.querySelectorAll('.subtitle-list-row').forEach(item => item.classList.remove('selected'));
                row.classList.add('selected');
                renderTimeline();
            };
            textarea.addEventListener('focus', selectSubtitle);
            textarea.addEventListener('blur', () => {
                if (state.wordHighlight) {
                    renderWordSpans();
                    textarea.hidden = true;
                    wordsContainer.hidden = false;
                }
            });
            textarea.addEventListener('input', handleTextChange);
            textarea.addEventListener('keydown', event => {
                const currentIndex = state.subtitles.findIndex(item => item.id === subtitle.id);
                if (event.key === 'Backspace' && textarea.selectionStart === 0 && textarea.selectionEnd === 0 && currentIndex > 0) {
                    event.preventDefault();
                    mergeWithPrevious(currentIndex, textarea.value);
                } else if (event.key === 'Delete' && textarea.selectionStart === textarea.value.length && textarea.selectionEnd === textarea.value.length && currentIndex < state.subtitles.length - 1) {
                    event.preventDefault();
                    mergeWithPrevious(currentIndex + 1);
                } else if (event.key === 'Enter' && !event.shiftKey && !event.ctrlKey && !event.altKey) {
                    event.preventDefault();
                    splitAtTextCursor(subtitle.id, textarea.selectionStart, textarea.selectionEnd, textarea.value);
                }
            });
            wordsContainer.addEventListener('click', () => {
                selectSubtitle();
                textarea.hidden = false;
                wordsContainer.hidden = true;
                textarea.focus();
            });
            if (state.wordHighlight) textarea.hidden = true;
            else wordsContainer.hidden = true;
            row.addEventListener('click', event => {
                if (event.target === textarea || event.target === times || wordsContainer.contains(event.target)) return;
                selectSubtitle();
                if (!state.wordHighlight) textarea.focus();
            });
            row.addEventListener('contextmenu', event => handleContextMenu(event, subtitle));
            cell.append(wordsContainer, textarea);
            row.append(number, times, cell);
            previewArea.appendChild(row);
        });
        searchInput.addEventListener('input', event => {
            state.subtitleSearch = event.target.value;
            const query = state.subtitleSearch.trim().toLocaleLowerCase();
            previewArea.querySelectorAll('.subtitle-list-row').forEach(row => {
                row.hidden = !!query && !row.dataset.search.includes(query);
            });
        });
    }

    // --- Lógica de Waveform ---

    async function processAudioForWaveform(audioBuffer) {
        console.warn('[Audio] Iniciando processamento para waveform...', {
            canais: audioBuffer.numberOfChannels,
            amostras: audioBuffer.length,
            duração: audioBuffer.duration.toFixed(2) + 's',
            sampleRate: audioBuffer.sampleRate + 'Hz'
        });

        const rawData = audioBuffer.getChannelData(0); // Canal mono ou primeiro canal
        const samples = audioBuffer.length;
        const duration = audioBuffer.duration;

        // Calcula quantas amostras por pixel no zoom 1x
        const samplesPerPixel = Math.floor(samples / (duration * PIXELS_PER_SECOND));
        console.warn('[Audio] samplesPerPixel:', samplesPerPixel);

        const peaks = [];

        for (let i = 0; i < samples; i += samplesPerPixel) {
            let min = 1.0;
            let max = -1.0;
            for (let j = 0; j < samplesPerPixel && i + j < samples; j++) {
                const val = rawData[i + j];
                if (val < min) min = val;
                if (val > max) max = val;
            }
            peaks.push({ min, max });
        }

        console.warn('[Audio] Waveform processado com sucesso!', {
            totalPeaks: peaks.length,
            primeiroPeak: peaks[0],
            ultimoPeak: peaks[peaks.length - 1]
        });

        updateState({
            waveformData: peaks,
            audioDuration: duration
        });
        renderWaveform();
    }

    async function loadWaveformFromUrl(url) {
        try {
            const response = await fetch(url);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const audioBuffer = await audioContext.decodeAudioData(await response.arrayBuffer());
            await processAudioForWaveform(audioBuffer);
        } catch (error) {
            console.error('[Media] Não foi possível gerar waveform:', error);
        }
    }

    function applySubtitleConfig(config) {
        const nextSignature = JSON.stringify(config || {});
        const configChanged = nextSignature !== subtitleConfigSignature;
        subtitleConfigSignature = nextSignature;
        subtitleConfig = config;
        const assToCss = value => {
            const match = String(value || '').match(/&H[0-9A-Fa-f]{2}([0-9A-Fa-f]{2})([0-9A-Fa-f]{2})([0-9A-Fa-f]{2})&/);
            return match ? `#${match[3]}${match[2]}${match[1]}` : value;
        };
        const root = document.documentElement.style;
        root.setProperty('--subtitle-font', config.font || 'Arial');
        root.setProperty('--subtitle-size', `${config.base_size || 30}px`);
        root.setProperty('--subtitle-color', assToCss(config.base_color) || '#ffffff');
        root.setProperty('--subtitle-highlight', assToCss(config.highlight_color) || '#facc15');
        root.setProperty('--subtitle-outline-color', assToCss(config.outline_color) || '#000000');
        root.setProperty('--subtitle-outline-size', `${config.outline_thickness || 0}px`);
        root.setProperty('--subtitle-weight', config.bold ? '700' : '400');
        root.setProperty('--subtitle-style', config.italic ? 'italic' : 'normal');
        subtitleOverlay.style.bottom = `${Number(config.vertical_position || 54)}px`;
        subtitleOverlay.style.textAlign = ({1: 'left', 2: 'center', 3: 'right'})[config.alignment] || 'center';
        subtitleOverlay.style.textTransform = config.uppercase ? 'uppercase' : 'none';
        subtitleOverlay.style.background = Number(config.border_style) === 3 ? 'rgba(0,0,0,.7)' : 'transparent';
        if (configChanged) refreshProjectTrack();
    }

    function refreshProjectTrack() {
        if (!projectTrack) return;
        if (projectVttUrl) URL.revokeObjectURL(projectVttUrl);
        projectVttUrl = URL.createObjectURL(new Blob([buildProjectVtt()], { type: 'text/vtt' }));
        projectTrack.src = projectVttUrl;
        projectTrack.track.mode = 'showing';
    }

    function scheduleProjectTrackRefresh() {
        if (!useNativeVtt || !projectTrack) return;
        clearTimeout(vttRefreshTimer);
        vttRefreshTimer = setTimeout(refreshProjectTrack, 120);
    }

    function buildProjectVtt() {
        const timestamp = seconds => {
            const total = Math.max(0, Math.round(Number(seconds || 0) * 1000));
            const hours = Math.floor(total / 3600000);
            const minutes = Math.floor(total / 60000) % 60;
            const secs = Math.floor(total / 1000) % 60;
            return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}.${String(total % 1000).padStart(3, '0')}`;
        };
        const clean = value => {
            let text = String(value || '');
            if (subtitleConfig.remove_punctuation) text = text.replace(/[^\w\sÀ-ÿ'-]/g, '');
            return escapeHtml(subtitleConfig.uppercase ? text.toUpperCase() : text);
        };
        const mode = subtitleConfig.mode || 'highlight';
        const blockSize = Math.max(1, Number(subtitleConfig.words_per_block) || 3);
        const alignment = ({ 1: 'start', 2: 'center', 3: 'end' })[subtitleConfig.alignment] || 'center';
        const cues = [];

        state.subtitles.forEach(subtitle => {
            const words = getSubtitleWords(subtitle);
            if (!words.length) {
                const text = clean(subtitle.text);
                if (text) cues.push([subtitle.start, subtitle.end, text]);
                return;
            }
            for (let blockStart = 0; blockStart < words.length; blockStart += blockSize) {
                const block = words.slice(blockStart, blockStart + blockSize);
                if (mode === 'no_highlight') {
                    cues.push([block[0].start, block.at(-1).end, block.map(word => clean(word.word)).join(' ')]);
                    continue;
                }
                block.forEach((activeWord, index) => {
                    const end = index + 1 < block.length ? block[index + 1].start : activeWord.end;
                    const text = mode === 'word_by_word'
                        ? clean(activeWord.word)
                        : block.map(word => word === activeWord ? `<c.highlight>${clean(word.word)}</c>` : clean(word.word)).join(' ');
                    cues.push([activeWord.start, Math.max(end, activeWord.start + .01), text]);
                });
            }
        });
        return `WEBVTT\n\n${cues.filter(([, , text]) => text).map(([start, end, text]) => `${timestamp(start)} --> ${timestamp(end)} align:${alignment}\n${text}`).join('\n\n')}`;
    }

    function renderWaveform() {
        if (!state.waveformData || !waveformCanvas || !waveformCtx) {
            // Log apenas se já tivermos duração (já importou algo)
            if (state.audioDuration > 0) {
                console.warn('[Waveform] Dados não disponíveis:', {
                    hasData: !!state.waveformData,
                    hasCanvas: !!waveformCanvas,
                    hasCtx: !!waveformCtx
                });
            }
            return;
        }

        try {
            const scrollLeft = timelineScrollContainer.scrollLeft || 0;
            const viewportWidth = timelineScrollContainer.clientWidth || 1000;
            const height = 60;

            // --- OTIMIZAÇÃO CRÍTICA PARA ZOOM ALTO ---
            // Em vez de criar um canvas gigante (que crasha o browser > 32k px),
            // criamos um canvas do tamanho da tela e o movemos conforme o scroll.
            waveformCanvas.width = viewportWidth;
            waveformCanvas.height = height;
            waveformCanvas.style.width = `${viewportWidth}px`;
            waveformCanvas.style.left = `${scrollLeft}px`; // Segue o scroll

            waveformCtx.clearRect(0, 0, viewportWidth, height);
            waveformCtx.fillStyle = '#7289da';

            const peaks = state.waveformData;
            const middleY = height / 2;
            const amplitudeScale = height / 2;

            // Calcula a escala de tempo
            const totalWidth = state.audioDuration * PIXELS_PER_SECOND * state.zoomLevel;
            const pixelsPerPeak = totalWidth / peaks.length;

            if (!isFinite(pixelsPerPeak) || pixelsPerPeak <= 0) return;

            // Determina quais picos desenhar baseado no scroll
            const startIndex = Math.max(0, Math.floor(scrollLeft / pixelsPerPeak));
            const endIndex = Math.min(peaks.length, Math.ceil((scrollLeft + viewportWidth) / pixelsPerPeak));

            console.log('[Waveform] Renderizando viewport:', {
                zoom: state.zoomLevel.toFixed(1) + 'x',
                totalWidth: totalWidth.toFixed(0) + 'px',
                viewportWidth,
                peaksInRange: endIndex - startIndex
            });

            for (let i = startIndex; i < endIndex; i++) {
                // Posição X relativa ao início da timeline
                const xTimeline = i * pixelsPerPeak;
                // Posição X relativa ao canvas (viewport)
                const xCanvas = xTimeline - scrollLeft;

                const peak = peaks[i];
                if (!peak) continue;

                const minY = middleY + (peak.min * amplitudeScale);
                const maxY = middleY + (peak.max * amplitudeScale);
                const peakHeight = Math.max(1, maxY - minY);

                waveformCtx.fillRect(xCanvas, minY, Math.max(1, pixelsPerPeak), peakHeight);
            }
        } catch (err) {
            console.error('[Waveform] Erro fatal na renderização:', err);
        }
    }

    // --- Handlers de Eventos ---

    importJsonBtn.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (event) => {
            let json = JSON.parse(event.target.result);

            // Detecta formato e converte se for Premiere
            const format = detectJSONFormat(json);
            if (format === 'premiere') {
                console.log('[Import] Detectado formato Premiere, convertendo...');
                json = convertPremiereToWhisperX(json);
            }

            const newSubs = (json.segments || []).map((s, i) => ({
                ...s,
                id: generateId() + "_import_" + Date.now() + i, // ID único para evitar conflitos no merge
                track: state.activeTrack // Força a importação para a camada ativa
            }));

            // Mantém legendas das OUTRAS tracks, mas limpa a track ATIVA para evitar sobreposição
            const otherTracksSubs = state.subtitles.filter(s => (s.track || 'Track 1') !== state.activeTrack);
            const mergedSubs = [...otherTracksSubs, ...newSubs].sort((a, b) => a.start - b.start);

            updateSubtitles(mergedSubs);

            // Limpa o input para permitir importar o mesmo arquivo novamente se necessário
            importJsonBtn.value = '';
        };
        reader.readAsText(file);
    });

    importMediaBtn.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        removeYouTubePlayer();

        console.log('[Media] Arquivo selecionado:', {
            nome: file.name,
            tipo: file.type,
            tamanho: (file.size / 1024 / 1024).toFixed(2) + 'MB'
        });

        const url = URL.createObjectURL(file);
        updateState({ mediaUrl: url });
        if (mediaFileName) mediaFileName.textContent = file.name;
        mediaPlayer.src = url;
        mediaPlayer.style.display = 'block';
        videoPlaceholder.style.display = 'none';

        mediaPlayer.addEventListener('loadedmetadata', () => {
            console.log('[Media] Metadata carregado:', {
                duração: mediaPlayer.duration.toFixed(2) + 's'
            });
            updateState({ mediaDuration: mediaPlayer.duration });
            renderTimeline();
            updateTimecodeDisplays();
        });

        // Processa o áudio para gerar o waveform
        console.log('[Media] Iniciando processamento de áudio...');
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const arrayBuffer = await file.arrayBuffer();
            const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
            await processAudioForWaveform(audioBuffer);
        } catch (err) {
            console.error('[Media] ERRO ao processar waveform:', err);
        }
    });

    importYouTubeBtn?.addEventListener('click', () => {
        const url = prompt('Cole um link do YouTube ou um link direto de vídeo (.mp4, .webm etc.):');
        if (url === null || !url.trim()) return;
        const value = url.trim();
        const videoId = extractYouTubeId(value);
        try {
            if (videoId) loadYouTubeVideo(videoId);
            else if (/^https?:\/\//i.test(value)) loadVideoLink(value);
            else throw new Error('invalid');
        } catch {
            alert('Link inválido. Use uma URL http(s) de vídeo ou do YouTube.');
        }
    });

    saveJsonBtn.addEventListener('click', () => {
        exportModal.style.display = 'flex';
    });

    cancelExportBtn.addEventListener('click', () => {
        exportModal.style.display = 'none';
    });

    confirmExportBtn.addEventListener('click', () => {
        const format = exportFormatSelect.value;
        const trackMode = exportTrackModeSelect.value;

        let segmentsToSave = state.subtitles;
        if (trackMode === 'active') {
            segmentsToSave = state.subtitles.filter(s => (s.track || 'Track 1') === state.activeTrack);
        }

        // Ordena por tempo de início para garantir integridade em formatos sequenciais
        segmentsToSave.sort((a, b) => a.start - b.start);

        let content = '';
        let mimeType = '';
        let fileName = '';

        if (format === 'json') {
            const cleanSegments = segmentsToSave.map(({ id, ...rest }) => ({
                ...rest,
                track: undefined
            }));
            content = JSON.stringify({ segments: cleanSegments }, null, 2);
            mimeType = 'application/json';
            fileName = (trackMode === 'active' ? `subtitles-whisperx-${state.activeTrack}` : 'subtitles-whisperx-all') + '.json';
        } else if (format === 'premiere') {
            const premiereData = convertWhisperXToPremiere({ segments: segmentsToSave });
            content = JSON.stringify(premiereData, null, 2);
            mimeType = 'application/json';
            fileName = (trackMode === 'active' ? `subtitles-premiere-${state.activeTrack}` : 'subtitles-premiere-all') + '.json';
        } else if (format === 'srt') {
            content = convertToSRT(segmentsToSave);
            mimeType = 'text/plain';
            fileName = (trackMode === 'active' ? `subtitles-${state.activeTrack}` : 'subtitles-all') + '.srt';
        } else if (format === 'tsv') {
            content = convertToTSV(segmentsToSave);
            mimeType = 'text/tab-separated-values';
            fileName = (trackMode === 'active' ? `subtitles-${state.activeTrack}` : 'subtitles-all') + '.tsv';
        }

        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = fileName;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        exportModal.style.display = 'none';
    });

    function formatTimeSRT(seconds) {
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = Math.floor(seconds % 60);
        const ms = Math.floor((seconds % 1) * 1000);

        return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')},${ms.toString().padStart(3, '0')}`;
    }

    function extractYouTubeId(url) {
        return url.match(/(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=|shorts\/))([\w-]{11})/)?.[1] || null;
    }

    function removeYouTubePlayer() {
        ytVideoId = null;
        ytReady = false;
        try { ytPlayer?.stopVideo(); } catch {}
        document.getElementById('youtube-player-container').style.display = 'none';
    }

    function loadVideoLink(url) {
        removeYouTubePlayer();
        if (state.mediaUrl?.startsWith('blob:')) URL.revokeObjectURL(state.mediaUrl);
        updateState({ mediaUrl: url, mediaDuration: 0, waveformData: null, audioDuration: 0 });
        mediaPlayer.src = url;
        mediaPlayer.onloadedmetadata = () => {
            updateState({ mediaDuration: mediaPlayer.duration || 0 });
            renderTimeline();
            updateTimecodeDisplays();
        };
        mediaPlayer.style.display = 'block';
        mediaPlayer.load();
        loadWaveformFromUrl(url);
        videoPlaceholder.style.display = 'none';
        if (mediaFileName) mediaFileName.textContent = `Link: ${new URL(url).hostname}`;
    }

    function loadYouTubeVideo(videoId) {
        ytVideoId = videoId;
        mediaPlayer.pause();
        mediaPlayer.removeAttribute('src');
        mediaPlayer.style.display = 'none';
        videoPlaceholder.style.display = 'none';
        document.getElementById('youtube-player-container').style.display = 'block';
        if (mediaFileName) mediaFileName.textContent = `YouTube: youtu.be/${videoId}`;
        const create = () => {
            ytPlayer = new YT.Player('youtube-player', {
                width: '100%', height: '100%', videoId,
                playerVars: { autoplay: 0, controls: 0, rel: 0, modestbranding: 1, disablekb: 1, enablejsapi: 1, origin: location.origin },
                events: {
                    onReady: event => {
                        ytReady = true;
                        const duration = event.target.getDuration();
                        updateState({ mediaDuration: duration || 0 });
                        renderTimeline();
                        updateTimecodeDisplays();
                    },
                    onStateChange: event => {
                        if (event.data === YT.PlayerState.ENDED && state.isPlaying) stopPlayback();
                    },
                    onError: () => alert('Este vídeo não permite reprodução incorporada. Tente um link direto de mídia.')
                }
            });
        };
        if (window.YT?.Player) create();
        else {
            if (!document.getElementById('youtube-iframe-api')) {
                const script = document.createElement('script');
                script.id = 'youtube-iframe-api';
                script.src = 'https://www.youtube.com/iframe_api';
                document.head.append(script);
            }
            window.onYouTubeIframeAPIReady = create;
        }
    }

    function formatClock(seconds) {
        const value = Math.max(0, Number(seconds) || 0);
        const hours = Math.floor(value / 3600);
        const minutes = Math.floor((value % 3600) / 60);
        const secs = (value % 60).toFixed(3).padStart(6, '0');
        return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${secs}`;
    }

    function convertToSRT(segments) {
        return segments.map((s, i) => {
            return `${i + 1}\n${formatTimeSRT(s.start)} --> ${formatTimeSRT(s.end)}\n${s.text}\n`;
        }).join('\n');
    }

    function convertToTSV(segments) {
        const header = "start\tend\ttext\n";
        const rows = segments.map(s => `${s.start.toFixed(3)}\t${s.end.toFixed(3)}\t${s.text.replace(/\t/g, ' ').replace(/\n/g, ' ')}`);
        return header + rows.join('\n');
    }

    // --- Helpers de Conversão de Formato (Adobe Premiere) ---

    function detectJSONFormat(data) {
        if (!data || !data.segments || data.segments.length === 0) return 'unknown';
        const first = data.segments[0];
        if (first.words && first.words.length > 0) {
            const firstWord = first.words[0];
            if ('confidence' in firstWord && 'eos' in firstWord) return 'premiere';
            if ('score' in firstWord || 'word' in firstWord) return 'whisperx';
        }
        if (first.start !== undefined && first.end !== undefined && first.text !== undefined) return 'whisperx';
        return 'unknown';
    }

    function convertPremiereToWhisperX(data) {
        const whisperData = { segments: [] };
        data.segments.forEach(seg => {
            const words = (seg.words || []).map(w => ({
                word: w.text,
                start: w.start,
                end: Number((w.start + w.duration).toFixed(3)),
                score: w.confidence || 1.0
            }));

            if (words.length > 0) {
                whisperData.segments.push({
                    start: words[0].start,
                    end: words[words.length - 1].end,
                    text: words.map(w => w.word).join(' '),
                    words: words
                });
            }
        });
        return whisperData;
    }

    function convertWhisperXToPremiere(data) {
        const premiereData = { language: "pt-BR", segments: [] };
        const speakerId = "Speaker 1"; // Simplificado

        data.segments.forEach(seg => {
            const premWords = (seg.words || []).map((w, i, arr) => ({
                confidence: w.score || 1.0,
                duration: Number((w.end - w.start).toFixed(3)),
                eos: i === arr.length - 1,
                start: w.start,
                tags: [],
                text: w.word,
                type: "word"
            }));

            if (premWords.length > 0) {
                premiereData.segments.push({
                    duration: Number((premWords[premWords.length - 1].start + premWords[premWords.length - 1].duration - premWords[0].start).toFixed(3)),
                    language: "pt-BR",
                    speaker: speakerId,
                    start: premWords[0].start,
                    words: premWords
                });
            }
        });
        return premiereData;
    }

    addSubtitleBtn.addEventListener('click', () => {
        const newSubtitle = {
            id: generateId(),
            start: state.cursorPosition,
            end: state.cursorPosition + 2,
            text: t('new_subtitle_text'),
            track: state.activeTrack,
            words: [{ word: t('new_subtitle_text'), start: state.cursorPosition, end: state.cursorPosition + 2 }],
        };
        const newSubs = [...state.subtitles, newSubtitle];
        newSubs.sort((a, b) => a.start - b.start);
        updateSubtitles(newSubs);
    });

    playPauseBtn.addEventListener('click', handlePlayPause);
    shuttleReverseBtn?.addEventListener('click', () => startShuttle(-1));
    shuttleForwardBtn?.addEventListener('click', () => startShuttle(1));

    function updateThemeButton() {
        if (!themeToggleBtn) return;
        const isDark = document.documentElement.dataset.theme === 'dark';
        themeToggleBtn.textContent = isDark ? '☀' : '☾';
        themeToggleBtn.title = isDark ? 'Usar tema claro' : 'Usar tema escuro';
    }

    themeToggleBtn?.addEventListener('click', () => {
        const nextTheme = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
        document.documentElement.dataset.theme = nextTheme;
        localStorage.setItem('theme', nextTheme);
        updateThemeButton();
    });
    window.addEventListener('storage', updateThemeButton);
    updateThemeButton();

    // Listeners de Camadas (Tracks)
    trackSelector.addEventListener('change', (e) => {
        updateState({ activeTrack: e.target.value });
        renderTimeline();
    });

    addTrackBtn.addEventListener('click', () => {
        const name = prompt(t('prompt_new_track'), `${t('track_prefix')} ${state.tracks.length + 1}`);
        if (name && !state.tracks.includes(name)) {
            const newTracks = [...state.tracks, name];
            updateState({ tracks: newTracks, activeTrack: name });
            renderTimeline();
        }
    });

    // Listener para o checkbox de auto-gerar caracteres
    autoGenerateCharsCheckbox.addEventListener('change', (e) => {
        updateState({ autoGenerateChars: e.target.checked });
        renderTimeline();
    });

    const savedControls = [
        [deleteOnShortenCheckbox, 'deleteOnShorten', 'subtitle_editor:delete_on_shorten'],
        [followPlaybackCheckbox, 'followPlayback', 'subtitle_editor:follow_playback'],
        [wordHighlightCheckbox, 'wordHighlight', 'subtitle_editor:word_highlight'],
        [snapEnabledCheckbox, 'snapEnabled', 'subtitle_editor:snap_enabled'],
        [snapKeyOnlyCheckbox, 'snapKeyOnly', 'subtitle_editor:snap_key_only']
    ];
    savedControls.forEach(([control, field, key]) => {
        if (!control) return;
        control.checked = state[field];
        control.addEventListener('change', event => {
            updateState({ [field]: event.target.checked });
            safeStorage.setItem(key, event.target.checked);
            if (field === 'wordHighlight') renderPreviewArea();
            if (field === 'followPlayback' && event.target.checked) updateFollowAndWordHighlight();
        });
    });
    if (snapGapMsInput) {
        snapGapMsInput.value = state.snapGapMs;
        snapGapMsInput.addEventListener('change', event => {
            const value = Math.max(0, Math.min(2000, Number(event.target.value) || 50));
            updateState({ snapGapMs: value });
            safeStorage.setItem('subtitle_editor:snap_gap_ms', value);
            event.target.value = value;
        });
    }

    // Listener para scroll da timeline (re-renderiza waveform)
    let scrollTimeout;
    timelineScrollContainer.addEventListener('scroll', () => {
        clearTimeout(scrollTimeout);
        scrollTimeout = setTimeout(() => {
            renderWaveform();
        }, 16); // ~60fps
    });

    // --- Lógica de Interação da Timeline ---
    function handleWordMoveStart(e, subtitleIndex, wordIndex) {
        e.preventDefault();
        e.stopPropagation();
        const initialSub = state.subtitles[subtitleIndex];
        const initialWord = initialSub.words?.[wordIndex];
        const wordEl = e.target.closest('.word');
        if (!initialWord || !wordEl) return;

        const startX = e.clientX;
        const duration = Math.max(.001, initialWord.end - initialWord.start);
        const previousEnd = wordIndex ? initialSub.words[wordIndex - 1].end : initialSub.start;
        const nextStart = wordIndex < initialSub.words.length - 1 ? initialSub.words[wordIndex + 1].start : initialSub.end;
        let finalStart = initialWord.start;
        wordEl.setPointerCapture?.(e.pointerId);

        function onPointerMove(moveEvent) {
            if (moveEvent.pointerId !== e.pointerId) return;
            moveEvent.preventDefault();
            const delta = (moveEvent.clientX - startX) / (PIXELS_PER_SECOND * state.zoomLevel);
            const maxStart = nextStart - duration;
            finalStart = maxStart >= previousEnd
                ? Math.max(previousEnd, Math.min(initialWord.start + delta, maxStart))
                : initialWord.start;
            wordEl.style.left = `${(finalStart - initialSub.start) * PIXELS_PER_SECOND * state.zoomLevel}px`;
        }

        function onPointerUp(upEvent) {
            if (upEvent.pointerId !== e.pointerId) return;
            const newSubs = [...state.subtitles];
            const words = initialSub.words.map((word, index) => index === wordIndex
                ? { ...word, start: finalStart, end: finalStart + duration }
                : { ...word });
            newSubs[subtitleIndex] = { ...initialSub, words };
            updateSubtitles(newSubs, true);
            wordEl.removeEventListener('pointermove', onPointerMove);
            wordEl.removeEventListener('pointerup', onPointerUp);
            wordEl.removeEventListener('pointercancel', onPointerUp);
        }

        wordEl.addEventListener('pointermove', onPointerMove);
        wordEl.addEventListener('pointerup', onPointerUp);
        wordEl.addEventListener('pointercancel', onPointerUp);
    }

    function handleWordResizeStart(e, subtitleIndex, wordIndex) {
        e.stopPropagation();
        if (e.type === 'touchstart') e.preventDefault();
        const startX = getClientX(e);
        const minDuration = 0.001; // Duração hiper mínima

        const originalSubs = JSON.parse(JSON.stringify(state.subtitles));
        const subtitle = originalSubs[subtitleIndex];
        const words = subtitle.words;
        const currentWord = words[wordIndex];
        const nextWord = words[wordIndex + 1];
        const originalBoundary = currentWord.end;
        const subStart = subtitle.start;
        const subEnd = subtitle.end;
        const subDuration = subEnd - subStart;

        // Calcula totalWordTime para CSS widths (mesma lógica do render)
        let totalWordTime = 0;
        words.forEach(w => {
            if (w.start !== undefined && w.end !== undefined) {
                totalWordTime += (w.end - w.start);
            }
        });
        if (totalWordTime <= 0) totalWordTime = subDuration;

        // Calcula o limite REAL máximo para a direita:
        // Cascateia pelas palavras seguintes até o fim do bloco
        let trueMaxBoundary;
        const isLastWord = (wordIndex + 1 === words.length - 1);
        if (isLastWord) {
            // A próxima palavra é a última: pode ir até o fim do bloco
            trueMaxBoundary = subEnd - minDuration;
        } else {
            // Pega o espaço disponível cascateando: cada palavra subsequente
            // pode ser comprimida até minDuration
            let maxAvailable = subEnd;
            for (let i = words.length - 1; i > wordIndex + 1; i--) {
                maxAvailable -= minDuration; // cada palavra precisa de pelo menos minDuration
            }
            trueMaxBoundary = maxAvailable - minDuration; // espaço para nextWord
        }

        // Limite mínimo: currentWord deve ter pelo menos minDuration
        const trueMinBoundary = currentWord.start + minDuration;

        // Localiza os elementos DOM para atualização direta
        const blockEl = timelineContent.querySelectorAll('.subtitle-block')[subtitleIndex];
        let wordEls = null;
        if (blockEl) {
            wordEls = blockEl.querySelectorAll('.word');
        }

        function onMouseMove(moveEvent) {
            if (moveEvent.type === 'touchmove') moveEvent.preventDefault();
            const currentX = getClientX(moveEvent);
            const deltaX = (currentX - startX) / (PIXELS_PER_SECOND * state.zoomLevel);

            let newBoundary = originalBoundary + deltaX;
            newBoundary = Math.max(newBoundary, trueMinBoundary);
            newBoundary = Math.min(newBoundary, trueMaxBoundary);

            // Calcula os novos tempos de cada palavra afetada
            // A palavra atual (currentWord) tem seu end ajustado
            const newCurrentEnd = newBoundary;
            // A próxima palavra tem seu start ajustado
            let newNextStart = newBoundary;
            // Se a boundary foi empurrada além do nextWord.end original,
            // precisamos expandir o nextWord.end (e cascatear)
            let newNextEnd = Math.max(nextWord.end, newBoundary + minDuration);

            // Se não é a última, cascateia as palavras seguintes
            if (!isLastWord) {
                for (let i = wordIndex + 2; i < words.length; i++) {
                    const w = words[i];
                    const prevEnd = (i === wordIndex + 2) ? newNextEnd : words[i - 1].end;
                    if (w.start < newNextEnd) {
                        // Empurra esta palavra
                        const wDuration = Math.max(w.end - w.start, minDuration);
                        words[i] = { ...w, start: newNextEnd, end: Math.max(newNextEnd + minDuration, w.end) };
                        newNextEnd = words[i].end;
                    }
                }
            }

            // Atualiza APENAS o CSS dos elementos DOM existentes (sem re-render!)
                if (wordEls) {
                    // Atualiza a palavra atual
                    if (wordEls[wordIndex]) {
                        const dur = newCurrentEnd - currentWord.start;
                        wordEls[wordIndex].style.width = `${dur * PIXELS_PER_SECOND * state.zoomLevel}px`;
                    }
                    // Atualiza a próxima palavra
                    if (wordEls[wordIndex + 1]) {
                        const dur = newNextEnd - newNextStart;
                        wordEls[wordIndex + 1].style.left = `${(newNextStart - subtitle.start) * PIXELS_PER_SECOND * state.zoomLevel}px`;
                        wordEls[wordIndex + 1].style.width = `${dur * PIXELS_PER_SECOND * state.zoomLevel}px`;
                    }
                }

            // Guarda os valores calculados para uso no mouseup
            onMouseMove._lastBoundary = newBoundary;
            onMouseMove._newNextEnd = newNextEnd;
        }
        onMouseMove._lastBoundary = originalBoundary;
        onMouseMove._newNextEnd = nextWord.end;

        function onMouseUp(event) {
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
            document.removeEventListener('touchmove', onMouseMove);
            document.removeEventListener('touchend', onMouseUp);

            const finalBoundary = onMouseMove._lastBoundary;
            const finalNextEnd = onMouseMove._newNextEnd;

            // Persiste as mudanças no estado e re-renderiza
            const finalSubs = JSON.parse(JSON.stringify(originalSubs));
            const finalWords = finalSubs[subtitleIndex].words;

            finalWords[wordIndex].end = finalBoundary;
            finalWords[wordIndex + 1].start = finalBoundary;
            finalWords[wordIndex + 1].end = finalNextEnd;

            // Cascateia as palavras seguintes se necessário
            for (let i = wordIndex + 2; i < finalWords.length; i++) {
                const prevEnd = finalWords[i - 1].end;
                if (finalWords[i].start < prevEnd) {
                    const origDur = Math.max(words[i].end - words[i].start, minDuration);
                    finalWords[i].start = prevEnd;
                    finalWords[i].end = Math.max(prevEnd + minDuration, finalWords[i].end);
                }
            }

            // Finalmente, atualiza o estado e grava no histórico
            updateSubtitles(finalSubs, true);
        }

        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);
        document.addEventListener('touchmove', onMouseMove, { passive: false });
        document.addEventListener('touchend', onMouseUp);
    }

    function handleCharResizeStart(e, subtitleIndex, charIndex) {
        e.stopPropagation();
        if (e.type === 'touchstart') e.preventDefault();
        const startX = getClientX(e);
        const minDuration = 0.001; // Duração mínima para um caractere

        const originalSubs = JSON.parse(JSON.stringify(state.subtitles));
        const subtitle = originalSubs[subtitleIndex];
        const currentChar = subtitle.chars[charIndex];
        const nextChar = subtitle.chars[charIndex + 1];

        function onMouseMove(moveEvent) {
            const currentX = getClientX(moveEvent);
            const deltaX = (currentX - startX) / (PIXELS_PER_SECOND * state.zoomLevel);

            let newBoundary = currentChar.end + deltaX;
            newBoundary = Math.max(newBoundary, currentChar.start + minDuration);
            newBoundary = Math.min(newBoundary, nextChar.end - minDuration);

            const tempSubs = JSON.parse(JSON.stringify(originalSubs));
            tempSubs[subtitleIndex].chars[charIndex].end = newBoundary;
            tempSubs[subtitleIndex].chars[charIndex + 1].start = newBoundary;

            updateSubtitles(tempSubs, false); // Atualiza UI sem salvar histórico
        }

        function onMouseUp(event) {
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
            document.removeEventListener('touchmove', onMouseMove);
            document.removeEventListener('touchend', onMouseUp);

            const finalSubs = JSON.parse(JSON.stringify(state.subtitles));
            const finalSubtitle = finalSubs[subtitleIndex];

            // Recalcula a fronteira final para precisão máxima
            const currentX = event.changedTouches ? event.changedTouches[0].clientX : event.clientX;
            const finalDeltaX = (currentX - startX) / (PIXELS_PER_SECOND * state.zoomLevel);
            let finalBoundary = currentChar.end + finalDeltaX;
            finalBoundary = Math.max(finalBoundary, currentChar.start + minDuration);
            finalBoundary = Math.min(finalBoundary, nextChar.end - minDuration);

            finalSubtitle.chars[charIndex].end = finalBoundary;
            finalSubtitle.chars[charIndex + 1].start = finalBoundary;

            updateSubtitles(finalSubs, true); // Salva a alteração no histórico
        }

        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);
        document.addEventListener('touchmove', onMouseMove, { passive: false });
        document.addEventListener('touchend', onMouseUp);
    }

    function getSnapPoints(ignoreSubId) {
        const points = [0, state.cursorPosition];
        state.subtitles.forEach(sub => {
            if (sub.id !== ignoreSubId) {
                points.push(sub.start);
                points.push(sub.end);
            }
        });
        return points;
    }

    function shouldSnap(event) {
        return state.snapEnabled && !event.altKey && (!state.snapKeyOnly || event.ctrlKey || event.shiftKey);
    }

    function hideSnapGuide() {
        if (snapVerticalGuide) snapVerticalGuide.style.display = 'none';
    }

    function findSnap(time, snapPoints) {
        const thresholdTime = state.snapGapMs / 1000;
        let closestDist = thresholdTime;
        let snapTime = time;

        snapPoints.forEach(pt => {
            const dist = Math.abs(pt - time);
            if (dist < closestDist) {
                closestDist = dist;
                snapTime = pt;
            }
        });
        if (snapTime !== time && snapVerticalGuide) {
            snapVerticalGuide.style.display = 'block';
            snapVerticalGuide.style.left = `${snapTime * PIXELS_PER_SECOND * state.zoomLevel}px`;
        } else hideSnapGuide();
        return snapTime;
    }

    function handleMoveStart(e, index) {
        if (e.button !== 0) return;
        e.preventDefault();
        e.stopPropagation();
        const startX = e.clientX;
        const initialSub = state.subtitles[index];
        const initialStart = initialSub.start;
        const duration = initialSub.end - initialSub.start;
        const dragArea = e.currentTarget;
        const block = dragArea.closest('.subtitle-block');
        let finalStart = initialStart;
        dragArea.setPointerCapture?.(e.pointerId);

        function resolveStart(clientX, event) {
            const deltaX = (clientX - startX) / (PIXELS_PER_SECOND * state.zoomLevel);
            let newStart = Math.max(0, initialStart + deltaX);
            let newEnd = newStart + duration;

            if (shouldSnap(event)) {
                const snapPoints = getSnapPoints(initialSub.id);
                const snappedStart = findSnap(newStart, snapPoints);
                const snappedEnd = findSnap(newEnd, snapPoints);

                if (snappedStart !== newStart && Math.abs(snappedStart - newStart) <= Math.abs(snappedEnd - newEnd)) {
                    newStart = snappedStart;
                    newEnd = newStart + duration;
                } else if (snappedEnd !== newEnd) {
                    newEnd = snappedEnd;
                    newStart = newEnd - duration;
                }
            }

            // --- Lógica antiborreamento (Prevenir sobreposição) ---
            const trackSubs = state.subtitles.filter(s => (s.track || 'Track 1') === (initialSub.track || 'Track 1') && s.id !== initialSub.id);
            let minStart = 0;
            let maxEnd = Infinity;

            trackSubs.forEach(s => {
                if (s.end <= initialStart + 0.001) minStart = Math.max(minStart, s.end);
                if (s.start >= initialSub.end - 0.001) maxEnd = Math.min(maxEnd, s.start);
            });

            if (newStart < minStart) {
                newStart = minStart;
                newEnd = newStart + duration;
            }
            if (newEnd > maxEnd) {
                newEnd = maxEnd;
                newStart = newEnd - duration;
                if (newStart < minStart) newStart = minStart;
            }
            return Math.max(0, newStart);
        }

        function onPointerMove(moveEvent) {
            if (moveEvent.pointerId !== e.pointerId) return;
            moveEvent.preventDefault();
            finalStart = resolveStart(moveEvent.clientX, moveEvent);
            block.style.left = `${finalStart * PIXELS_PER_SECOND * state.zoomLevel}px`;
        }

        function onPointerUp(upEvent) {
            if (upEvent.pointerId !== e.pointerId) return;
            const newSubs = [...state.subtitles];
            const movedSub = {
                ...initialSub,
                start: finalStart,
                end: finalStart + duration,
                words: (initialSub.words || []).map(w => ({
                    ...w,
                    start: w.start + (finalStart - initialSub.start),
                    end: w.end + (finalStart - initialSub.start)
                }))
            };
            newSubs[index] = movedSub;
            updateSubtitles(newSubs, false);
            recordHistory();
            hideSnapGuide();
            dragArea.removeEventListener('pointermove', onPointerMove);
            dragArea.removeEventListener('pointerup', onPointerUp);
            dragArea.removeEventListener('pointercancel', onPointerUp);
        }

        dragArea.addEventListener('pointermove', onPointerMove);
        dragArea.addEventListener('pointerup', onPointerUp);
        dragArea.addEventListener('pointercancel', onPointerUp);
    }

    function handleResizeStart(e, index, direction) {
        e.stopPropagation();
        if (e.type === 'touchstart') e.preventDefault();
        const startX = getClientX(e);
        const initialSub = state.subtitles[index];
        const { start, end } = initialSub;

        function onMouseMove(moveEvent) {
            const currentX = getClientX(moveEvent);
            const deltaX = (currentX - startX) / (PIXELS_PER_SECOND * state.zoomLevel);
            let newStart = start, newEnd = end;

            if (direction === 'left') {
                newStart = Math.max(0, start + deltaX);
                if (shouldSnap(moveEvent)) {
                    const snapPoints = getSnapPoints(initialSub.id);
                    newStart = findSnap(newStart, snapPoints);
                }
                if (newStart >= end - 0.01) newStart = end - 0.01;
            } else {
                newEnd = Math.max(start + 0.01, end + deltaX);
                if (shouldSnap(moveEvent)) {
                    const snapPoints = getSnapPoints(initialSub.id);
                    newEnd = findSnap(newEnd, snapPoints);
                }
            }

            // --- Lógica antiborreamento (Prevenir sobreposição) ---
            const trackSubs = state.subtitles.filter(s => (s.track || 'Track 1') === (initialSub.track || 'Track 1') && s.id !== initialSub.id);
            let minStart = 0;
            let maxEnd = Infinity;

            trackSubs.forEach(s => {
                if (s.end <= start + 0.001) minStart = Math.max(minStart, s.end);
                if (s.start >= end - 0.001) maxEnd = Math.min(maxEnd, s.start);
            });

            if (direction === 'left' && newStart < minStart) {
                newStart = minStart;
            } else if (direction === 'right' && newEnd > maxEnd) {
                newEnd = maxEnd;
            }

            const newSubs = [...state.subtitles];
            const updatedSub = { ...initialSub, start: newStart, end: newEnd };

            const oldDuration = end - start;
            const newDuration = newEnd - newStart;

            // Padrão (sem CTRL): reajusta tudo proporcionalmente. 
            // Com CTRL: cresce/encolhe apenas a palavra da ponta sem mudar as outras.
            const useProportional = !moveEvent.ctrlKey;

            const originalWords = initialSub.words || [];

            if (state.deleteOnShorten && newDuration < oldDuration) {
                const keepWithinRange = item => item.end > newStart && item.start < newEnd;
                updatedSub.words = originalWords.filter(keepWithinRange).map(word => ({
                    ...word,
                    start: Math.max(word.start, newStart),
                    end: Math.min(word.end, newEnd)
                }));
                updatedSub.text = updatedSub.words.map(word => word.word).join(' ');
                if (initialSub.chars?.length) {
                    updatedSub.chars = initialSub.chars.filter(keepWithinRange).map(character => ({
                        ...character,
                        start: Math.max(character.start, newStart),
                        end: Math.min(character.end, newEnd)
                    }));
                }
            } else if (useProportional) {
                const scale = newDuration / oldDuration;
                updatedSub.words = originalWords.map(w => ({
                    ...w,
                    start: newStart + (w.start - start) * scale,
                    end: newStart + (w.end - start) * scale
                }));

                // Faz o mesmo para chars, se existirem
                if (initialSub.chars && initialSub.chars.length > 0) {
                    updatedSub.chars = initialSub.chars.map(c => ({
                        ...c,
                        start: newStart + (c.start - start) * scale,
                        end: newStart + (c.end - start) * scale
                    }));
                }
            } else {
                // Aumentando (sem Shift): estica apenas a primeira ou última palavra/letra
                updatedSub.words = JSON.parse(JSON.stringify(originalWords));
                if (updatedSub.words.length > 0) {
                    if (direction === 'left') {
                        // Limite: a primeira palavra não pode ter duração negativa
                        let maxAllowedStart = updatedSub.words[0].end - 0.001;
                        if (newStart > maxAllowedStart) newStart = maxAllowedStart;
                        updatedSub.start = newStart;
                        updatedSub.words[0].start = newStart;
                    } else {
                        // Limite: a última palavra não pode ter duração negativa
                        let minAllowedEnd = updatedSub.words[updatedSub.words.length - 1].start + 0.001;
                        if (newEnd < minAllowedEnd) newEnd = minAllowedEnd;
                        updatedSub.end = newEnd;
                        updatedSub.words[updatedSub.words.length - 1].end = newEnd;
                    }
                }

                if (initialSub.chars && initialSub.chars.length > 0) {
                    updatedSub.chars = JSON.parse(JSON.stringify(initialSub.chars));
                    if (updatedSub.chars.length > 0) {
                        if (direction === 'left') {
                            updatedSub.chars[0].start = newStart;
                        } else {
                            updatedSub.chars[updatedSub.chars.length - 1].end = newEnd;
                        }
                    }
                }
            }

            newSubs[index] = updatedSub;
            updateSubtitles(newSubs, false);
        }

        function onMouseUp() {
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
            document.removeEventListener('touchmove', onMouseMove);
            document.removeEventListener('touchend', onMouseUp);
            recordHistory();
            hideSnapGuide();
        }

        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);
        document.addEventListener('touchmove', onMouseMove, { passive: false });
        document.addEventListener('touchend', onMouseUp);
    }

    function handleSelectSubtitle(e, subtitle) {
        e.stopPropagation();
        closeContextMenu();

        if (e.ctrlKey) {
            const newSelection = state.selectedSubtitles.includes(subtitle)
                ? state.selectedSubtitles.filter(s => s !== subtitle)
                : [...state.selectedSubtitles, subtitle];
            updateState({ selectedSubtitles: newSelection, lastSelected: subtitle });
        } else if (e.shiftKey && state.lastSelected) {
            const startIdx = state.subtitles.indexOf(state.lastSelected);
            const endIdx = state.subtitles.indexOf(subtitle);
            if (startIdx !== -1 && endIdx !== -1) {
                const selection = state.subtitles.slice(Math.min(startIdx, endIdx), Math.max(startIdx, endIdx) + 1);
                updateState({ selectedSubtitles: selection });
            }
        } else {
            updateState({ selectedSubtitles: [subtitle], lastSelected: subtitle });
        }
        renderTimeline();
        renderPreviewArea();
    }

    function handleTextChange(e) {
        const newText = e.target.value;
        const selectedId = e.target.closest('.subtitle-list-row')?.dataset.subId;
        if (!selectedId) return;

        // Sempre busca o índice atual para evitar referências obsoletas
        const index = state.subtitles.findIndex(s => s.id === selectedId);
        if (index === -1) return;

        const oldSub = state.subtitles[index];
        const newWordsList = newText.trim().split(/\s+/).filter(w => w.length > 0);

        // Lógica de sincronização local de palavras (melhorada)
        let updatedWords = [];
        const oldWords = oldSub.words || [];

        if (newWordsList.length === oldWords.length) {
            // Mesma quantidade: preserva tempos, muda apenas o texto das palavras
            updatedWords = newWordsList.map((word, i) => ({ ...oldWords[i], word: word }));
        } else {
            // Quantidade diferente: redistribui uniformemente sobre a duração total da legenda
            const duration = oldSub.end - oldSub.start;
            const wDur = duration / Math.max(1, newWordsList.length);
            updatedWords = newWordsList.map((word, i) => ({
                word: word,
                start: oldSub.start + i * wDur,
                end: oldSub.start + (i + 1) * wDur
            }));
        }

        const updatedSub = {
            ...oldSub,
            text: newText,
            words: updatedWords,
            chars: []
        };

        const newSubs = [...state.subtitles];
        newSubs[index] = updatedSub;

        // Atualiza estado e seleção (mantendo a referência nova)
        updateState({
            subtitles: newSubs,
            selectedSubtitles: [updatedSub]
        });

        renderTimeline();
        scheduleProjectTrackRefresh();

        // A versão estática mantém o ajuste local; não depende do endpoint do Dublador.
        previewArea.querySelector(`.subtitle-list-row[data-sub-id="${CSS.escape(String(selectedId))}"]`)?._renderWordSpans?.();
    }

    // Adiciona evento para gravar histórico quando terminar de editar
    previewArea.addEventListener('focusout', (e) => {
        if (e.target.tagName === 'TEXTAREA') {
            recordHistory();
        }
    });

    // --- Lógica do Cursor e Playback ---

    function setCursorPosition(pos) {
        updateState({ cursorPosition: Math.max(0, pos) });
        renderCursor();
        if (ytVideoId && ytReady && !state.isPlaying) {
            try { ytPlayer.seekTo(state.cursorPosition, true); } catch {}
        }
    }

    function updateTransportControls() {
        playPauseBtn.textContent = state.isPlaying ? t('pause') : t('play');
        shuttleReverseBtn?.classList.toggle('transport-active', state.isPlaying && state.playbackDirection < 0);
        shuttleForwardBtn?.classList.toggle('transport-active', state.isPlaying && state.playbackDirection > 0);
        if (playbackSpeed) playbackSpeed.textContent = `${state.isPlaying && state.playbackDirection < 0 ? '-' : ''}${state.playbackRate}x`;
    }

    function stopPlayback() {
        updateState({ isPlaying: false, playbackRate: 1 });
        mediaPlayer.pause();
        if (ytVideoId && ytReady) {
            try { ytPlayer.pauseVideo(); } catch {}
        }
        updateTransportControls();
    }

    function startShuttle(direction) {
        const alreadyRunning = state.isPlaying;
        const rate = alreadyRunning && state.playbackDirection === direction
            ? Math.min(8, state.playbackRate * 2)
            : 1;
        updateState({ isPlaying: true, playbackDirection: direction, playbackRate: rate });
        mediaPlayer.playbackRate = rate;
        lastTime = performance.now();
        if (direction > 0 && mediaPlayer.src) mediaPlayer.play().catch(() => {});
        else mediaPlayer.pause();
        if (ytVideoId && ytReady) {
            try {
                if (direction > 0) {
                    ytPlayer.setPlaybackRate(rate);
                    ytPlayer.playVideo();
                } else ytPlayer.pauseVideo();
            } catch {}
        }
        updateTransportControls();
        if (!alreadyRunning) playbackLoop();
    }

    function handlePlayPause() {
        if (state.isPlaying) stopPlayback();
        else startShuttle(1);
    }

    let lastTime = performance.now();
    function playbackLoop() {
        if (!state.isPlaying) return;

        const now = performance.now();
        const delta = (now - lastTime) / 1000;
        lastTime = now;
        if (state.playbackDirection < 0) {
            if (!state.isDraggingCursor) {
                const nextPosition = Math.max(0, state.cursorPosition - delta * state.playbackRate);
                if (mediaPlayer.src) mediaPlayer.currentTime = nextPosition;
                setCursorPosition(nextPosition);
                if (nextPosition === 0) {
                    stopPlayback();
                    return;
                }
            }
        } else if (mediaPlayer.src) {
            if (!state.isDraggingCursor) {
                setCursorPosition(mediaPlayer.currentTime);
            }
        } else if (ytVideoId && ytReady) {
            if (!state.isDraggingCursor) {
                try { setCursorPosition(ytPlayer.getCurrentTime()); } catch { setCursorPosition(state.cursorPosition + delta); }
            }
        } else if (!state.isDraggingCursor) {
            setCursorPosition(state.cursorPosition + delta * state.playbackRate);
        }

        // Auto-scroll da timeline
        const cursorPx = state.cursorPosition * PIXELS_PER_SECOND * state.zoomLevel;
        const containerWidth = timelineScrollContainer.clientWidth;
        const scrollLeft = timelineScrollContainer.scrollLeft;

        if (cursorPx < scrollLeft || cursorPx > scrollLeft + containerWidth) {
            timelineScrollContainer.scrollLeft = cursorPx - containerWidth / 2;
        }

        requestAnimationFrame(playbackLoop);
    }

    mediaPlayer.addEventListener('ended', () => {
        if (state.isPlaying) stopPlayback();
    });

    // --- Lógica de Teclado e Contexto ---

    window.addEventListener('keydown', async (e) => {
        const tag = e.target.tagName;
        if (tag === 'INPUT' || tag === 'TEXTAREA') return;

        let handled = true;
        switch (e.key) {
            case ' ': e.preventDefault(); handlePlayPause(); break;
            case 'j': case 'J': startShuttle(-1); break;
            case 'l': case 'L': startShuttle(1); break;
            case 'Delete': handleDelete(); break;
            case 'k': case 'K': await handleSplit(); break;
            case 'g': case 'G': handleMerge(); break;
            case 'c': if (e.ctrlKey) handleCopy(); break;
            case 'v': if (e.ctrlKey) handlePaste(); break;
            case 'z': if (e.ctrlKey) handleUndo(); break;
            case 'y': if (e.ctrlKey) handleRedo(); break;
            case 'ArrowLeft': setCursorPosition(state.cursorPosition - (e.shiftKey ? 1 : 0.1)); break;
            case 'ArrowRight': setCursorPosition(state.cursorPosition + (e.shiftKey ? 1 : 0.1)); break;
            default: handled = false; break;
        }
        if (handled) e.preventDefault();
    });

    function handleDelete() {
        if (state.selectedSubtitles.length === 0) return;
        const idsToDelete = new Set(state.selectedSubtitles.map(s => state.subtitles.indexOf(s)));
        const newSubs = state.subtitles.filter((_, index) => !idsToDelete.has(index));
        updateSubtitles(newSubs);
        updateState({ selectedSubtitles: [] });
    }

    function handleSplit() {
        const subtitleToSplit = state.selectedSubtitles.length === 1
            ? state.selectedSubtitles[0]
            : state.subtitles.find(sub => state.cursorPosition > sub.start && state.cursorPosition < sub.end);

        if (!subtitleToSplit) return;

        const splitTime = state.cursorPosition;

        // Evita divisões muito próximas das bordas (0.05s de tolerância)
        if (splitTime <= subtitleToSplit.start + 0.05 || splitTime >= subtitleToSplit.end - 0.05) return;

        let beforeText = "";
        let afterText = "";
        let beforeWords = [];
        let afterWords = [];

        // Se tiver palavras (WhisperX), divide respeitando limites das palavras
        if (subtitleToSplit.words && subtitleToSplit.words.length > 0) {
            let splitIndex = 0;

            for (let i = 0; i < subtitleToSplit.words.length; i++) {
                const w = subtitleToSplit.words[i];
                // Se o cursor estiver antes do MEIO da palavra, corta antes dela
                // Se estiver depois do MEIO, a palavra fica no primeiro bloco
                const wordCenter = (w.start + w.end) / 2;
                if (splitTime < wordCenter) {
                    splitIndex = i;
                    break;
                }
                // Se for a última palavra e passou do meio, o corte é após a última
                if (i === subtitleToSplit.words.length - 1) {
                    splitIndex = subtitleToSplit.words.length;
                }
            }

            beforeWords = subtitleToSplit.words.slice(0, splitIndex);
            afterWords = subtitleToSplit.words.slice(splitIndex);

            beforeText = beforeWords.map(w => w.word).join(' ').trim();
            afterText = afterWords.map(w => w.word).join(' ').trim();
        } else {
            // Sem palavras: divide texto proporcionalmente ao tempo
            const duration = subtitleToSplit.end - subtitleToSplit.start;
            const progress = (splitTime - subtitleToSplit.start) / duration;
            const text = subtitleToSplit.text || "";
            // Garante índice válido
            const splitCharIndex = Math.max(0, Math.min(text.length, Math.round(text.length * progress)));

            beforeText = text.substring(0, splitCharIndex).trim();
            afterText = text.substring(splitCharIndex).trim();
        }

        // Cria novos objetos de legenda
        const sub1 = {
            ...subtitleToSplit,
            id: generateId(),
            end: splitTime,
            text: beforeText,
            words: beforeWords,
            chars: [] // Limpa chars para regenerar se necessário
        };

        const sub2 = {
            ...subtitleToSplit,
            id: generateId(),
            start: splitTime,
            text: afterText,
            words: afterWords,
            chars: []
        };

        // Substitui a original pelas duas novas
        const index = state.subtitles.findIndex(s => s.id === subtitleToSplit.id);
        if (index === -1) return;

        const newSubs = [...state.subtitles];
        newSubs.splice(index, 1, sub1, sub2);

        updateSubtitles(newSubs);
        updateState({ selectedSubtitles: [] });
    }

    function mergeWithPrevious(index, textOverride = null) {
        if (index <= 0 || index >= state.subtitles.length) return;
        const previous = state.subtitles[index - 1];
        const current = state.subtitles[index];
        const currentText = textOverride === null ? current.text : textOverride;
        const text = `${(previous.text || '').trimEnd()} ${(currentText || '').trimStart()}`.trim();
        const merged = {
            ...previous,
            end: Math.max(previous.end, current.end),
            text,
            words: [...getSubtitleWords(previous), ...getSubtitleWords({ ...current, text: currentText })],
            chars: [...(previous.chars || []), ...(current.chars || [])]
        };
        const subtitles = [...state.subtitles];
        subtitles.splice(index - 1, 2, merged);
        updateSubtitles(subtitles);
        updateState({ selectedSubtitles: [merged], lastSelected: merged });
        renderPreviewArea(true);
    }

    function splitAtTextCursor(id, selectionStart, selectionEnd, value) {
        const index = state.subtitles.findIndex(subtitle => subtitle.id === id);
        if (index === -1) return;
        const subtitle = state.subtitles[index];
        const beforeText = value.slice(0, selectionStart).trim();
        const afterText = value.slice(selectionEnd).trim();
        if (!beforeText || !afterText) return;
        const allWords = getSubtitleWords(subtitle);
        const beforeCount = beforeText.split(/\s+/).filter(Boolean).length;
        const splitTime = allWords[beforeCount - 1] && allWords[beforeCount]
            ? (allWords[beforeCount - 1].end + allWords[beforeCount].start) / 2
            : subtitle.start + (subtitle.end - subtitle.start) * beforeText.length / value.length;
        const before = {
            ...subtitle,
            id: generateId(),
            end: Number(splitTime.toFixed(3)),
            text: beforeText,
            words: getSubtitleWords({ ...subtitle, end: splitTime, text: beforeText }),
            chars: []
        };
        const after = {
            ...subtitle,
            id: generateId(),
            start: Number(splitTime.toFixed(3)),
            text: afterText,
            words: getSubtitleWords({ ...subtitle, start: splitTime, text: afterText }),
            chars: []
        };
        const subtitles = [...state.subtitles];
        subtitles.splice(index, 1, before, after);
        updateSubtitles(subtitles);
        updateState({ selectedSubtitles: [after], lastSelected: after });
        renderPreviewArea(true);
    }

    function handleMerge() {
        if (state.selectedSubtitles.length < 2) return;
        const sorted = [...state.selectedSubtitles].sort((a, b) => a.start - b.start);
        const merged = {
            id: generateId(),
            start: sorted[0].start,
            end: sorted[sorted.length - 1].end,
            text: sorted.map(s => s.text).join(' '),
            words: sorted.flatMap(s => s.words || []),
        };

        const idsToMerge = new Set(state.selectedSubtitles.map(s => state.subtitles.indexOf(s)));
        let newSubs = state.subtitles.filter((_, index) => !idsToMerge.has(index));
        newSubs.push(merged);
        newSubs.sort((a, b) => a.start - b.start);

        updateSubtitles(newSubs);
        updateState({ selectedSubtitles: [merged] });
    }

    function handleCopy() {
        if (state.selectedSubtitles.length === 0) return;
        updateState({ copiedSubtitles: JSON.parse(JSON.stringify(state.selectedSubtitles)) });
    }

    function handlePaste() {
        if (state.copiedSubtitles.length === 0) return;
        const firstStart = Math.min(...state.copiedSubtitles.map(s => s.start));
        const newSubsToAdd = state.copiedSubtitles.map(sub => {
            const offset = sub.start - firstStart;
            const duration = sub.end - sub.start;
            const timeShift = (state.cursorPosition + offset) - sub.start;
            return {
                ...sub,
                id: generateId(),
                start: state.cursorPosition + offset,
                end: state.cursorPosition + offset + duration,
                track: state.activeTrack, // Cola na camada ativa!
                words: (sub.words || []).map(w => ({
                    ...w,
                    start: w.start + timeShift,
                    end: w.end + timeShift
                })),
                chars: (sub.chars || []).map(c => ({
                    ...c,
                    start: c.start !== undefined ? c.start + timeShift : undefined,
                    end: c.end !== undefined ? c.end + timeShift : undefined
                }))
            };
        });

        const newSubs = [...state.subtitles, ...newSubsToAdd];
        newSubs.sort((a, b) => a.start - b.start);
        updateSubtitles(newSubs);
    }

    function handleUndo() {
        if (state.historyIndex > 0) {
            const newIndex = state.historyIndex - 1;
            const subs = JSON.parse(JSON.stringify(state.history[newIndex]));
            updateState({ historyIndex: newIndex });
            updateSubtitles(subs, false); // Não grava novo histórico
            updateState({ selectedSubtitles: [] });
        }
    }

    function handleRedo() {
        if (state.historyIndex < state.history.length - 1) {
            const newIndex = state.historyIndex + 1;
            const subs = JSON.parse(JSON.stringify(state.history[newIndex]));
            updateState({ historyIndex: newIndex });
            updateSubtitles(subs, false);
            updateState({ selectedSubtitles: [] });
        }
    }

    function handleContextMenu(e, subtitle = null) {
        e.preventDefault();
        e.stopPropagation();

        contextMenu.style.display = 'block';
        contextMenu.style.left = `${e.pageX}px`;
        contextMenu.style.top = `${e.pageY}px`;
        contextMenu.innerHTML = ''; // Limpa

        if (subtitle && !state.selectedSubtitles.includes(subtitle)) {
            updateState({ selectedSubtitles: [subtitle] });
            renderTimeline();
            renderPreviewArea();
        }

        const actions = [];
        if (state.selectedSubtitles.length > 0) {
            if (state.selectedSubtitles.length === 1) actions.push({ label: t('split'), action: handleSplit });
            actions.push({ label: t('copy'), action: handleCopy });
            actions.push({ label: t('delete'), action: handleDelete });
            if (state.selectedSubtitles.length > 1) actions.push({ label: t('merge'), action: handleMerge });
        }
        if (state.copiedSubtitles.length > 0) {
            actions.push({ label: t('paste'), action: handlePaste });
        }
        actions.push({ label: t('undo'), action: handleUndo });
        actions.push({ label: t('redo'), action: handleRedo });

        actions.forEach(({ label, action }) => {
            const item = document.createElement('div');
            item.textContent = label;
            item.addEventListener('click', () => {
                action();
                closeContextMenu();
            });
            contextMenu.appendChild(item);
        });
    }

    function closeContextMenu() {
        contextMenu.style.display = 'none';
    }

    timelineFrame.addEventListener('contextmenu', handleContextMenu);

    // Long press no fundo do timeline para mobile
    let timelinePressTimer;
    timelineFrame.addEventListener('touchstart', (e) => {
        if (e.touches.length > 1) return; // ignora se for pinch
        timelinePressTimer = setTimeout(() => {
            handleContextMenu(e, null);
        }, 500);
    });
    timelineFrame.addEventListener('touchend', () => { clearTimeout(timelinePressTimer); });
    timelineFrame.addEventListener('touchmove', () => { clearTimeout(timelinePressTimer); });

    app.addEventListener('click', closeContextMenu);
    app.addEventListener('touchstart', closeContextMenu, { passive: true });

    timelineScrollContainer.addEventListener('wheel', (e) => {
        e.preventDefault();
        if (e.ctrlKey) {
            // --- LÓGICA DE ZOOM AVANÇADA (ZOOM EM DIREÇÃO AO CURSOR) ---

            // 1. Onde o mouse está em relação ao container que rola?
            const rect = timelineScrollContainer.getBoundingClientRect();
            const mouseX = e.clientX - rect.left;

            // 2. Em que ponto do tempo o cursor do mouse está?
            const timeAtMouse = (timelineScrollContainer.scrollLeft + mouseX) / (PIXELS_PER_SECOND * state.zoomLevel);

            // 3. Calcula o novo nível de zoom (com limites maiores)
            const delta = e.deltaY > 0 ? -0.2 : 0.2; // Aumenta a sensibilidade
            const newZoom = Math.max(0.2, Math.min(100, state.zoomLevel + delta)); // Limites: 0.2x até 100x

            // Se o zoom não mudou (atingiu o limite), não faz mais nada.
            if (newZoom === state.zoomLevel) return;

            updateState({ zoomLevel: newZoom });

            // 4. Após o zoom, a posição do tempo sob o mouse (timeAtMouse) agora corresponde a um novo valor em pixels.
            const newMousePxPos = timeAtMouse * PIXELS_PER_SECOND * state.zoomLevel;

            // 5. Ajusta a posição da barra de rolagem para que o ponto do tempo sob o mouse permaneça no mesmo lugar na tela.
            timelineScrollContainer.scrollLeft = newMousePxPos - mouseX;

        } else {
            // Scroll horizontal normal (Shift + Scroll ou touchpad)
            timelineScrollContainer.scrollLeft += e.deltaY;
        }
        renderTimeline();
        renderCursor();
    }, { passive: false });

    // Lógica de pinch-to-zoom mobile
    let initialPinchDist = null;
    let initialZoomStart = null;
    timelineScrollContainer.addEventListener('touchstart', (e) => {
        if (e.touches.length === 2) {
            e.preventDefault();
            const dx = e.touches[0].clientX - e.touches[1].clientX;
            const dy = e.touches[0].clientY - e.touches[1].clientY;
            initialPinchDist = Math.sqrt(dx * dx + dy * dy);
            initialZoomStart = state.zoomLevel;
        }
    }, { passive: false });

    timelineScrollContainer.addEventListener('touchmove', (e) => {
        if (e.touches.length === 2 && initialPinchDist) {
            e.preventDefault();
            const dx = e.touches[0].clientX - e.touches[1].clientX;
            const dy = e.touches[0].clientY - e.touches[1].clientY;
            const dist = Math.sqrt(dx * dx + dy * dy);
            const scale = dist / initialPinchDist;

            const newZoom = Math.max(0.2, Math.min(100, initialZoomStart * scale));

            if (newZoom !== state.zoomLevel) {
                // Foca o zoom no centro dos dois dedos
                const rect = timelineScrollContainer.getBoundingClientRect();
                const centerXPx = ((e.touches[0].clientX + e.touches[1].clientX) / 2) - rect.left;
                const timeAtCenter = (timelineScrollContainer.scrollLeft + centerXPx) / (PIXELS_PER_SECOND * state.zoomLevel);

                updateState({ zoomLevel: newZoom });

                const newCenterPx = timeAtCenter * PIXELS_PER_SECOND * state.zoomLevel;
                timelineScrollContainer.scrollLeft = newCenterPx - centerXPx;

                renderTimeline();
                renderCursor();
            }
        }
    }, { passive: false });

    timelineScrollContainer.addEventListener('touchend', (e) => {
        if (e.touches.length < 2) {
            initialPinchDist = null;
            initialZoomStart = null;
        }
    });

    // Atualiza a posição dos labels das tracks quando rola
    timelineScrollContainer.addEventListener('scroll', () => {
        const scrollLeft = timelineScrollContainer.scrollLeft;
        document.querySelectorAll('[data-track-label="true"]').forEach(label => {
            label.style.left = `${scrollLeft}px`;
        });
    });

    function handleTimelineCursorGrab(e) {
        // Se clicar em um bloco de legenda, handle OU no fundo de uma track, 
        // ou se for touch de pinch (2 dedos), não inicia o arraste do cursor (seek).
        if (e.target.closest('.subtitle-block') || e.target.closest('.resize-handle') || e.target.closest('.word-handle') || e.target.closest('.char-handle') || e.target.closest('.track-bg') || (e.touches && e.touches.length > 1)) {
            return;
        }

        const rect = timelineFrame.getBoundingClientRect();
        const updateCursorFromEvent = (event) => {
            const x = getClientX(event) - rect.left;
            let pos = Math.max(0, x / (PIXELS_PER_SECOND * state.zoomLevel));
            if (shouldSnap(event)) pos = findSnap(pos, getSnapPoints());
            else hideSnapGuide();
            setCursorPosition(pos);
        };

        updateCursorFromEvent(e);
        updateState({ isDraggingCursor: true });

        const onMouseMove = (moveEvent) => {
            updateCursorFromEvent(moveEvent);
        };

        const onMouseUp = () => {
            hideSnapGuide();
            updateState({ isDraggingCursor: false });
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
            document.removeEventListener('touchmove', onMouseMove);
            document.removeEventListener('touchend', onMouseUp);
        };

        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);
        document.addEventListener('touchmove', onMouseMove, { passive: false });
        document.addEventListener('touchend', onMouseUp);

        if (!e.ctrlKey && !e.shiftKey) {
            updateState({ selectedSubtitles: [] });
            renderTimeline();
            renderPreviewArea();
        }
    }

    timelineFrame.addEventListener('mousedown', handleTimelineCursorGrab);
    timelineFrame.addEventListener('touchstart', handleTimelineCursorGrab, { passive: true });

    function handleCursorInteraction(e) {
        e.stopPropagation();
        if (e.type === 'touchstart') e.preventDefault();
        const rect = timelineFrame.getBoundingClientRect();
        updateState({ isDraggingCursor: true });

        const onMouseMove = (moveEvent) => {
            const x = getClientX(moveEvent) - rect.left;
            let pos = Math.max(0, x / (PIXELS_PER_SECOND * state.zoomLevel));
            if (shouldSnap(moveEvent)) pos = findSnap(pos, getSnapPoints());
            else hideSnapGuide();
            setCursorPosition(pos);
        };

        const onMouseUp = () => {
            hideSnapGuide();
            updateState({ isDraggingCursor: false });
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
            document.removeEventListener('touchmove', onMouseMove);
            document.removeEventListener('touchend', onMouseUp);
        };

        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);
        document.addEventListener('touchmove', onMouseMove, { passive: false });
        document.addEventListener('touchend', onMouseUp);
    }

    cursor.addEventListener('mousedown', handleCursorInteraction);
    cursor.addEventListener('touchstart', handleCursorInteraction, { passive: false });

    // --- Inicialização ---
    initI18n(); // Carrega traduções primeiro
    renderTrackSelector();
    initResizers();
    updateSubtitles([]); // Grava o estado inicial no histórico
    loadProjectSubtitles();

    if (languageSelector) {
        languageSelector.addEventListener('change', (e) => {
            updateState({ language: e.target.value });
        });
    }

    if (splitPunctuationBtn) {
        splitPunctuationBtn.addEventListener('click', handleSplitByPunctuation);
    }
    if (mergePunctuationBtn) {
        mergePunctuationBtn.addEventListener('click', handleMergeByPunctuation);
    }
    if (syncWaveformBtn) {
        syncWaveformBtn.addEventListener('click', handleSyncWaveform);
    }

    function handleMergeByPunctuation() {
        const input = prompt('Limite máximo de caracteres após mesclar (0 = sem limite):', '80');
        if (input === null) return;
        const maxLength = Number.parseInt(input, 10) || 0;
        const track = state.activeTrack;
        const otherTracks = state.subtitles.filter(subtitle => (subtitle.track || 'Track 1') !== track);
        const subtitles = state.subtitles
            .filter(subtitle => (subtitle.track || 'Track 1') === track)
            .sort((a, b) => a.start - b.start);
        const merged = [];
        for (let index = 0; index < subtitles.length; index++) {
            let current = subtitles[index];
            while (index + 1 < subtitles.length && !/[.!?…。！？]$/.test((current.text || '').trimEnd())) {
                const next = subtitles[index + 1];
                const text = `${(current.text || '').trimEnd()} ${(next.text || '').trimStart()}`.trim();
                if (maxLength && text.length > maxLength) break;
                current = {
                    ...current,
                    id: generateId(),
                    end: Math.max(current.end, next.end),
                    text,
                    words: [...(current.words || []), ...(next.words || [])],
                    chars: [...(current.chars || []), ...(next.chars || [])]
                };
                index++;
            }
            merged.push(current);
        }
        updateSubtitles([...otherTracks, ...merged].sort((a, b) => a.start - b.start));
    }

    function handleSyncWaveform() {
        if (!state.waveformData?.length || !state.audioDuration) {
            alert('Carregue uma mídia com áudio antes de sincronizar.');
            return;
        }
        const track = state.activeTrack;
        const selectedIds = new Set(state.selectedSubtitles.map(subtitle => subtitle.id));
        const trackSubs = state.subtitles.filter(subtitle => (subtitle.track || 'Track 1') === track).sort((a, b) => a.start - b.start);
        const targets = selectedIds.size ? trackSubs.filter(subtitle => selectedIds.has(subtitle.id)) : trackSubs;
        if (!targets.length || (!selectedIds.size && !confirm(`Sincronizar as ${targets.length} legendas da camada ativa?`))) return;

        const peaks = state.waveformData;
        const step = state.audioDuration / peaks.length;
        const amplitude = time => {
            const peak = peaks[Math.max(0, Math.min(peaks.length - 1, Math.floor(time / step)))];
            return peak ? Math.max(0, peak.max - peak.min) : 0;
        };
        const floor = peaks.reduce((sum, peak) => sum + Math.max(0, peak.max - peak.min), 0) / peaks.length;
        const threshold = Math.max(.045, floor * 1.6);
        const targetIds = new Set(targets.map(subtitle => subtitle.id));
        const adjusted = trackSubs.map((subtitle, index) => {
            if (!targetIds.has(subtitle.id)) return subtitle;
            const minStart = index ? trackSubs[index - 1].end + .05 : 0;
            const maxEnd = index < trackSubs.length - 1 ? trackSubs[index + 1].start - .05 : state.audioDuration;
            let start = subtitle.start;
            let end = subtitle.end;
            for (let time = subtitle.start; time >= minStart && subtitle.start - time <= 1; time -= step) {
                if (amplitude(time) < threshold) { start = time + step; break; }
            }
            for (let time = subtitle.end; time <= maxEnd && time - subtitle.end <= 1; time += step) {
                if (amplitude(time) < threshold) { end = time; break; }
            }
            start = Math.max(minStart, Math.min(start, end - .35));
            end = Math.min(maxEnd, Math.max(end, start + .35));
            const oldDuration = Math.max(.01, subtitle.end - subtitle.start);
            const newDuration = end - start;
            return {
                ...subtitle,
                start: Number(start.toFixed(3)),
                end: Number(end.toFixed(3)),
                words: (subtitle.words || []).map(word => ({
                    ...word,
                    start: Number((start + (word.start - subtitle.start) / oldDuration * newDuration).toFixed(3)),
                    end: Number((start + (word.end - subtitle.start) / oldDuration * newDuration).toFixed(3))
                })),
                chars: []
            };
        });
        const others = state.subtitles.filter(subtitle => (subtitle.track || 'Track 1') !== track);
        updateSubtitles([...others, ...adjusted].sort((a, b) => a.start - b.start));
    }

    function handleSplitByPunctuation() {
        const punctuation = ['.', '!', '?', ')', 'よ', 'ね', 'の', 'さ', 'ぞ', 'な', 'か', '！', '。', '」', '…', ','];
        const input = prompt(t('prompt_max_chars'), "80");
        if (input === null) return;

        const maxLen = parseInt(input) || 0;
        let hasChanged = false;
        let newSubtitles = [];

        state.subtitles.forEach(sub => {
            const splitResults = smartSplitSubtitle(sub, punctuation, maxLen);
            if (splitResults.length > 1) hasChanged = true;
            newSubtitles = newSubtitles.concat(splitResults);
        });

        if (hasChanged) {
            updateSubtitles(newSubtitles.sort((a, b) => a.start - b.start));
            renderTimeline();
            renderPreviewArea();
        }
    }

    function smartSplitSubtitle(sub, punctuation, maxLen) {
        if (maxLen > 0 && sub.text.length <= maxLen) return [sub];

        if (!sub.words || sub.words.length === 0) {
            const text = sub.text.trim();
            const splitPos = findBestSplitPosition(text, punctuation, maxLen);

            if (splitPos === -1) return [sub];

            const part1 = text.substring(0, splitPos).trim();
            const part2 = text.substring(splitPos).trim();

            if (!part1 || !part2) return [sub];

            const duration = sub.end - sub.start;
            const t1 = (part1.length / text.length) * duration;

            const sub1 = { ...sub, id: generateId(), end: sub.start + t1, text: part1, words: [] };
            const sub2 = { ...sub, id: generateId(), start: sub.start + t1, text: part2, words: [] };

            return [sub1, ...smartSplitSubtitle(sub2, punctuation, maxLen)];
        }

        const bestWordIdx = findBestWordSplitIndex(sub.words, punctuation, maxLen);

        if (bestWordIdx === -1 || bestWordIdx === sub.words.length - 1) return [sub];

        const part1Words = sub.words.slice(0, bestWordIdx + 1);
        const part2Words = sub.words.slice(bestWordIdx + 1);

        const sub1 = {
            ...sub,
            id: generateId(),
            end: part1Words[part1Words.length - 1].end,
            text: part1Words.map(w => w.word).join(' ').trim(),
            words: part1Words
        };

        const sub2 = {
            ...sub,
            id: generateId(),
            start: part2Words[0].start,
            text: part2Words.map(w => w.word).join(' ').trim(),
            words: part2Words
        };

        return [sub1, ...smartSplitSubtitle(sub2, punctuation, maxLen)];
    }

    function findBestSplitPosition(text, punctuation, maxLen) {
        if (maxLen === 0) {
            for (let i = 0; i < text.length; i++) {
                if (punctuation.includes(text[i]) && i < text.length - 1) return i + 1;
            }
            return -1;
        }

        let bestPos = -1;
        for (let i = 0; i < text.length; i++) {
            if (punctuation.includes(text[i])) {
                const pos = i + 1;
                if (pos <= maxLen) bestPos = pos;
                else if (bestPos === -1) return pos;
                else break;
            }
        }
        return bestPos;
    }

    function findBestWordSplitIndex(words, punctuation, maxLen) {
        let runningText = "";
        let bestIdx = -1;

        for (let i = 0; i < words.length; i++) {
            runningText += (i === 0 ? "" : " ") + words[i].word.trim();
            const wordText = words[i].word.trim();
            const endsWithPunc = punctuation.some(p => wordText.endsWith(p));

            if (endsWithPunc) {
                if (maxLen === 0) return i;

                if (runningText.length <= maxLen) {
                    bestIdx = i;
                } else {
                    return bestIdx !== -1 ? bestIdx : i;
                }
            }
        }
        return bestIdx;
    }

    function initResizers() {
        // Resizer Horizontal (Ajusta Colunas do Grid)
        function handleResizerHStart(e) {
            e.preventDefault();
            resizerH.classList.add('active');

            const onMouseMove = (moveEvent) => {
                const workspaceRect = workspace.getBoundingClientRect();
                const x = getClientX(moveEvent) - workspaceRect.left;
                const percentage = (x / workspaceRect.width) * 100;

                if (percentage > 10 && percentage < 90) {
                    workspace.style.gridTemplateColumns = `${percentage}% 1fr`;
                    resizerH.style.left = `${percentage}%`;
                }
            };

            const onMouseUp = () => {
                resizerH.classList.remove('active');
                document.removeEventListener('mousemove', onMouseMove);
                document.removeEventListener('mouseup', onMouseUp);
                document.removeEventListener('touchmove', onMouseMove);
                document.removeEventListener('touchend', onMouseUp);
            };

            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
            document.addEventListener('touchmove', onMouseMove, { passive: false });
            document.addEventListener('touchend', onMouseUp);
        }

        resizerH.addEventListener('mousedown', handleResizerHStart);
        resizerH.addEventListener('touchstart', handleResizerHStart, { passive: false });

        // Resizer Vertical (Ajusta Linhas do Grid)
        function handleResizerVStart(e) {
            e.preventDefault();
            resizerV.classList.add('active');

            const onMouseMove = (moveEvent) => {
                const workspaceRect = workspace.getBoundingClientRect();
                const y = getClientY(moveEvent) - workspaceRect.top;
                const percentage = (y / workspaceRect.height) * 100;

                if (percentage > 20 && percentage < 80) {
                    workspace.style.gridTemplateRows = `${percentage}% 1fr`;
                    resizerV.style.top = `${percentage}%`;
                    if (!workspace.classList.contains('layout-916')) resizerH.style.height = `${percentage}%`;
                }
            };

            const onMouseUp = () => {
                resizerV.classList.remove('active');
                document.removeEventListener('mousemove', onMouseMove);
                document.removeEventListener('mouseup', onMouseUp);
                document.removeEventListener('touchmove', onMouseMove);
                document.removeEventListener('touchend', onMouseUp);
            };

            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
            document.addEventListener('touchmove', onMouseMove, { passive: false });
            document.addEventListener('touchend', onMouseUp);
        }

        resizerV.addEventListener('mousedown', handleResizerVStart);
        resizerV.addEventListener('touchstart', handleResizerVStart, { passive: false });

        // Toggle Modo 9:16
        toggleLayoutBtn.addEventListener('click', () => {
            workspace.classList.toggle('layout-916');
            const is916 = workspace.classList.contains('layout-916');

            if (is916) {
                // Modo 9:16: Reseta para proporção vertical padrão
                workspace.style.gridTemplateColumns = "1fr 350px";
                workspace.style.gridTemplateRows = "55% 1fr";
                resizerH.style.left = "calc(100% - 350px)";
                resizerH.style.height = "100%";
                resizerV.style.top = "55%";
            } else {
                // Modo Normal (16:9): Reseta para proporção wide
                workspace.style.gridTemplateColumns = "1fr 1fr";
                workspace.style.gridTemplateRows = "55% 1fr";
                resizerH.style.left = "50%";
                resizerH.style.height = "55%";
                resizerV.style.top = "55%";
            }
            updateIndicators();
        });

        // Posicionamento inicial dos resizers
        resizerH.style.left = "50%";
        resizerH.style.height = "55%";
        resizerV.style.top = "55%";
    }

    // --- Lógica de Busca e Substituição ---

    let searchResults = [];
    let currentSearchIndex = -1;

    function performSearch(query) {
        if (!query) {
            searchResults = [];
            currentSearchIndex = -1;
            return [];
        }

        const results = [];
        const lowerQuery = query.toLowerCase();

        state.subtitles.forEach((sub, index) => {
            if (sub.text.toLowerCase().includes(lowerQuery)) {
                results.push({ subtitle: sub, index: index });
            }
        });

        return results;
    }

    function updateSearchStatus(statusElement, count) {
        if (count === 0) {
            statusElement.textContent = t('no_results');
        } else {
            statusElement.textContent = `${currentSearchIndex + 1} / ${count} ${t('results_count')}`;
        }
    }

    function navigateToResult(index) {
        if (searchResults.length === 0) return;

        currentSearchIndex = index;
        if (currentSearchIndex < 0) currentSearchIndex = searchResults.length - 1;
        if (currentSearchIndex >= searchResults.length) currentSearchIndex = 0;

        const result = searchResults[currentSearchIndex];
        updateState({ selectedSubtitles: [result.subtitle] });

        // Não move mais o cursor - apenas seleciona a legenda
        // setCursorPosition(result.subtitle.start);

        // Scroll automático até o bloco na timeline
        const blockPx = result.subtitle.start * PIXELS_PER_SECOND * state.zoomLevel;
        const containerWidth = timelineScrollContainer.clientWidth;
        const scrollTarget = blockPx - (containerWidth / 2); // Centraliza o bloco
        timelineScrollContainer.scrollLeft = Math.max(0, scrollTarget);

        renderTimeline();
        renderPreviewArea();

        // Destaca o texto encontrado no preview
        highlightSearchTerm();
    }

    function highlightSearchTerm() {
        const textarea = previewArea.querySelector('.subtitle-list-row.selected textarea');
        if (!textarea || state.selectedSubtitles.length !== 1) return;

        const findText = findInput?.value || replaceFindInput?.value;
        if (!findText) return;

        const subtitle = state.selectedSubtitles[0];
        const text = subtitle.text;

        // Cria um elemento temporário para mostrar o destaque
        const highlightDiv = document.createElement('div');
        highlightDiv.style.padding = '10px';
        highlightDiv.style.background = '#2f3136';
        highlightDiv.style.borderRadius = '4px';
        highlightDiv.style.color = 'white';
        highlightDiv.style.marginBottom = '10px';
        highlightDiv.style.fontSize = '14px';
        highlightDiv.style.lineHeight = '1.5';

        // Destaca o termo de busca
        const regex = new RegExp(`(${findText})`, 'gi');
        const highlightedText = text.replace(regex, '<span class="search-highlight">$1</span>');
        highlightDiv.innerHTML = highlightedText;

        // Insere antes do textarea
        if (previewArea.querySelector('.search-highlight-container')) {
            previewArea.querySelector('.search-highlight-container').remove();
        }
        highlightDiv.className = 'search-highlight-container';
        textarea.parentElement.insertBefore(highlightDiv, textarea);
    }

    function replaceInSubtitle(subtitle, findText, replaceText) {
        const newText = subtitle.text.replace(new RegExp(findText, 'gi'), replaceText);

        // Se o texto não mudou, retorna sem modificar
        if (newText === subtitle.text) {
            return subtitle;
        }

        // Reconstrói as palavras a partir do novo texto
        const newWordsList = newText.trim().split(/\s+/).filter(w => w.length > 0);
        const duration = subtitle.end - subtitle.start;
        const wordDuration = duration / Math.max(1, newWordsList.length);

        const newWords = newWordsList.map((word, i) => ({
            word: word,
            start: subtitle.start + (i * wordDuration),
            end: subtitle.start + ((i + 1) * wordDuration),
            score: 1.0 // Define score padrão para palavras substituídas
        }));

        return {
            ...subtitle,
            text: newText,
            words: newWords,
            chars: [] // Limpa chars para regenerar
        };
    }

    // Event Listeners para Find Modal
    if (closeFindBtn) {
        closeFindBtn.addEventListener('click', () => {
            findModal.style.display = 'none';
            searchResults = [];
            currentSearchIndex = -1;
            // Remove highlight ao fechar
            const highlightContainer = previewArea.querySelector('.search-highlight-container');
            if (highlightContainer) highlightContainer.remove();
        });
    }

    if (findInput) {
        findInput.addEventListener('input', () => {
            const query = findInput.value;
            searchResults = performSearch(query);
            currentSearchIndex = searchResults.length > 0 ? 0 : -1;
            updateSearchStatus(findStatus, searchResults.length);

            if (searchResults.length > 0) {
                navigateToResult(0);
            }
        });

        findInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                if (e.shiftKey) {
                    navigateToResult(currentSearchIndex - 1);
                } else {
                    navigateToResult(currentSearchIndex + 1);
                }
                updateSearchStatus(findStatus, searchResults.length);
            }
        });
    }

    if (findNextBtn) {
        findNextBtn.addEventListener('click', () => {
            navigateToResult(currentSearchIndex + 1);
            updateSearchStatus(findStatus, searchResults.length);
        });
    }

    if (findPreviousBtn) {
        findPreviousBtn.addEventListener('click', () => {
            navigateToResult(currentSearchIndex - 1);
            updateSearchStatus(findStatus, searchResults.length);
        });
    }

    // Event Listeners para Replace Modal
    if (closeReplaceBtn) {
        closeReplaceBtn.addEventListener('click', () => {
            replaceModal.style.display = 'none';
            searchResults = [];
            currentSearchIndex = -1;
            // Remove highlight ao fechar
            const highlightContainer = previewArea.querySelector('.search-highlight-container');
            if (highlightContainer) highlightContainer.remove();
        });
    }

    if (replaceFindInput) {
        replaceFindInput.addEventListener('input', () => {
            const query = replaceFindInput.value;
            searchResults = performSearch(query);
            currentSearchIndex = searchResults.length > 0 ? 0 : -1;
            updateSearchStatus(replaceStatus, searchResults.length);

            if (searchResults.length > 0) {
                navigateToResult(0);
            }
        });

        replaceFindInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                if (e.shiftKey) {
                    navigateToResult(currentSearchIndex - 1);
                } else {
                    navigateToResult(currentSearchIndex + 1);
                }
                updateSearchStatus(replaceStatus, searchResults.length);
            }
        });
    }

    if (replaceNextBtn) {
        replaceNextBtn.addEventListener('click', () => {
            navigateToResult(currentSearchIndex + 1);
            updateSearchStatus(replaceStatus, searchResults.length);
        });
    }

    if (replacePreviousBtn) {
        replacePreviousBtn.addEventListener('click', () => {
            navigateToResult(currentSearchIndex - 1);
            updateSearchStatus(replaceStatus, searchResults.length);
        });
    }

    if (replaceOneBtn) {
        replaceOneBtn.addEventListener('click', () => {
            if (searchResults.length === 0) return;

            const findText = replaceFindInput.value;
            const replaceText = replaceWithInput.value;

            const result = searchResults[currentSearchIndex];
            const subIndex = state.subtitles.findIndex(s => s.id === result.subtitle.id);

            if (subIndex !== -1) {
                const newSubs = [...state.subtitles];
                newSubs[subIndex] = replaceInSubtitle(newSubs[subIndex], findText, replaceText);
                updateSubtitles(newSubs);

                // Atualiza a busca
                searchResults = performSearch(findText);
                if (searchResults.length > 0 && currentSearchIndex >= searchResults.length) {
                    currentSearchIndex = searchResults.length - 1;
                }
                updateSearchStatus(replaceStatus, searchResults.length);

                if (searchResults.length > 0) {
                    navigateToResult(currentSearchIndex);
                }
            }
        });
    }

    if (replaceAllBtn) {
        replaceAllBtn.addEventListener('click', () => {
            if (searchResults.length === 0) return;

            const findText = replaceFindInput.value;
            const replaceText = replaceWithInput.value;

            const newSubs = state.subtitles.map(sub => {
                if (sub.text.toLowerCase().includes(findText.toLowerCase())) {
                    return replaceInSubtitle(sub, findText, replaceText);
                }
                return sub;
            });

            updateSubtitles(newSubs);

            // Atualiza a busca
            searchResults = performSearch(findText);
            currentSearchIndex = -1;
            updateSearchStatus(replaceStatus, searchResults.length);
        });
    }

    // Atalhos de teclado Ctrl+F e Ctrl+H
    window.addEventListener('keydown', (e) => {
        // Verifica se está digitando em algum input/textarea
        const tag = e.target.tagName;
        const isTyping = (tag === 'INPUT' || tag === 'TEXTAREA');

        // Ctrl+F para buscar (não abre se estiver digitando, exceto nos campos de busca)
        if (e.ctrlKey && e.key === 'f') {
            if (!isTyping || e.target === findInput || e.target === replaceFindInput) {
                e.preventDefault();
                findModal.style.display = 'flex';
                setTimeout(() => findInput.focus(), 100);
            }
        }

        // Ctrl+H para substituir (não abre se estiver digitando, exceto nos campos de substituição)
        if (e.ctrlKey && e.key === 'h') {
            if (!isTyping || e.target === findInput || e.target === replaceFindInput || e.target === replaceWithInput) {
                e.preventDefault();
                replaceModal.style.display = 'flex';
                setTimeout(() => replaceFindInput.focus(), 100);
            }
        }

        // ESC para fechar modals
        if (e.key === 'Escape') {
            findModal.style.display = 'none';
            replaceModal.style.display = 'none';
            searchResults = [];
            currentSearchIndex = -1;
            // Remove highlight ao fechar
            const highlightContainer = previewArea.querySelector('.search-highlight-container');
            if (highlightContainer) highlightContainer.remove();
        }
    });

});
