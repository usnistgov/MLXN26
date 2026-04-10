document.addEventListener('DOMContentLoaded', () => {
    const board = document.getElementById('agendaBoard');

    if (!board) {
        return;
    }

    const errorBox = document.getElementById('scheduleError');
    const detailTitle = document.getElementById('agenda-detail-title');
    const detailSummary = document.getElementById('agendaDetailSummary');
    const detailDay = document.getElementById('agendaDetailDay');
    const detailTime = document.getElementById('agendaDetailTime');
    const detailType = document.getElementById('agendaDetailType');
    const detailLocation = document.getElementById('agendaDetailLocation');
    const detailSpeaker = document.getElementById('agendaDetailSpeaker');
    const detailAffiliation = document.getElementById('agendaDetailAffiliation');
    const detailAbstract = document.getElementById('agendaDetailAbstract');

    const showError = (message) => {
        errorBox.textContent = message;
        errorBox.classList.remove('d-none');
    };

    const parseClockTime = (timeString) => {
        const [hours, minutes] = timeString.split(':').map(Number);
        return hours * 60 + minutes;
    };

    const formatClockTime = (timeString) => {
        const totalMinutes = parseClockTime(timeString);
        const hours24 = Math.floor(totalMinutes / 60);
        const minutes = totalMinutes % 60;
        const suffix = hours24 >= 12 ? 'PM' : 'AM';
        const hours12 = hours24 % 12 || 12;
        return `${hours12}:${String(minutes).padStart(2, '0')} ${suffix}`;
    };

    const formatRange = (start, end) => `${formatClockTime(start)} - ${formatClockTime(end)}`;

    const setDetailContent = (event, dayLookup) => {
        detailTitle.textContent = event.title;
        detailSummary.textContent = event.summary || 'No summary provided yet.';
        detailDay.textContent = dayLookup.get(event.day)?.label || event.day;
        detailTime.textContent = formatRange(event.start, event.end);
        detailType.textContent = event.typeLabel || event.themeLabel || 'Session';
        detailLocation.textContent = event.location || 'To be announced';
        detailSpeaker.textContent = event.speaker || 'To be announced';
        detailAffiliation.textContent = event.affiliation || 'Not provided';
        detailAbstract.textContent = event.abstract || 'Not provided';
    };

    const buildSchedule = (data) => {
        const { conference, days, events } = data;
        const slotMinutes = conference.slotMinutes;
        const startMinutes = parseClockTime(conference.timeRange.start);
        const endMinutes = parseClockTime(conference.timeRange.end);
        const totalSlots = (endMinutes - startMinutes) / slotMinutes;
        const dayLookup = new Map(days.map((day) => [day.id, day]));
        const eventsByDay = new Map(days.map((day) => [day.id, []]));
        let activeButton = null;

        events.forEach((event) => {
            if (eventsByDay.has(event.day)) {
                eventsByDay.get(event.day).push(event);
            }
        });

        days.forEach((day) => {
            eventsByDay.get(day.id).sort((left, right) => parseClockTime(left.start) - parseClockTime(right.start));
        });

        board.style.setProperty('--agenda-day-count', days.length);
        board.innerHTML = '';

        const grid = document.createElement('div');
        grid.className = 'agenda-grid';

        const corner = document.createElement('div');
        corner.className = 'agenda-corner';
        corner.textContent = 'Time';
        grid.appendChild(corner);

        days.forEach((day) => {
            const header = document.createElement('div');
            header.className = 'agenda-day-header';
            header.textContent = day.label;
            grid.appendChild(header);
        });

        const timeColumn = document.createElement('div');
        timeColumn.className = 'agenda-time-column';

        for (let slot = 0; slot < totalSlots; slot += 1) {
            const label = document.createElement('div');
            label.className = 'agenda-time-label';
            label.textContent = formatClockTime(`${String(Math.floor((startMinutes + slot * slotMinutes) / 60)).padStart(2, '0')}:${String((startMinutes + slot * slotMinutes) % 60).padStart(2, '0')}`);
            timeColumn.appendChild(label);
        }

        grid.appendChild(timeColumn);

        days.forEach((day) => {
            const track = document.createElement('div');
            track.className = 'agenda-day-track';
            track.style.setProperty('--agenda-slot-count', totalSlots);

            eventsByDay.get(day.id).forEach((event) => {
                const eventStart = parseClockTime(event.start);
                const eventEnd = parseClockTime(event.end);
                const startSlot = (eventStart - startMinutes) / slotMinutes;
                const span = Math.max(0.5, (eventEnd - eventStart) / slotMinutes);
                const button = document.createElement('button');

                button.type = 'button';
                button.className = `agenda-event theme-${event.theme || 'neutral'}`;
                button.style.top = `calc(${startSlot} * var(--agenda-slot-height))`;
                button.style.height = `calc(${span} * var(--agenda-slot-height))`;
                if (span < 1) {
                    button.classList.add('agenda-event-compact');
                }
                button.dataset.eventId = event.id;

                const title = document.createElement('span');
                title.className = 'agenda-event-title';
                title.textContent = event.title;
                button.appendChild(title);

                if (event.subtitle) {
                    const subtitle = document.createElement('span');
                    subtitle.className = 'agenda-event-subtitle';
                    subtitle.textContent = event.subtitle;
                    button.appendChild(subtitle);
                }

                button.addEventListener('click', () => {
                    if (activeButton) {
                        activeButton.classList.remove('is-active');
                    }

                    activeButton = button;
                    activeButton.classList.add('is-active');
                    setDetailContent(event, dayLookup);
                });

                track.appendChild(button);
            });

            grid.appendChild(track);
        });

        board.appendChild(grid);

        const firstEvent = board.querySelector('.agenda-event');
        if (firstEvent) {
            firstEvent.click();
        }
    };

    fetch('schedule-data.json', { cache: 'no-store' })
        .then((response) => {
            if (!response.ok) {
                throw new Error(`Unable to load schedule-data.json (${response.status}).`);
            }

            return response.json();
        })
        .then((data) => {
            buildSchedule(data);
        })
        .catch((error) => {
            showError(`${error.message} Serve the site over HTTP while editing locally so the browser can request the JSON file.`);
        });
});
