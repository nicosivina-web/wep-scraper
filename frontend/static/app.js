function wepApp() {
  return {
    // navegación
    tab: 'buscar',
    mobileNavOpen: false,

    // países
    countries: [],

    // búsqueda
    form: { pais: 'AR', nicho: '', ciudad: '', radio_km: null, cantidad: 20 },
    buscando: false,
    avisoDuplicado: null,

    // leads
    leads: [],
    totalLeads: 0,
    pagina: 1,
    pageSize: 50,
    cargandoLeads: false,
    filtros: { q: '', pais: '', nicho: '', ciudad: '', con_email: false, con_ig: false, sin_contactar: false },
    seleccionados: [],

    // panel lateral
    panelLead: null,
    panelTags: [],
    nuevoTag: '',

    // export
    exportOpen: false,
    columnasDisponibles: [
      'nombre', 'pais_nombre', 'nicho', 'ciudad', 'direccion', 'email',
      'telefono', 'whatsapp', 'ig', 'facebook', 'web', 'categoria',
      'rating', 'tags', 'estado', 'contactado_at', 'created_at',
    ],
    columnasExport: ['nombre', 'pais_nombre', 'nicho', 'ciudad', 'email', 'telefono', 'whatsapp', 'ig', 'web', 'tags', 'estado'],

    // búsquedas
    busquedas: [],

    // enrichment
    enrichStatus: { en_curso: false, total: 0, procesados: 0, encontrados: 0, errores: 0 },
    _enrichWasRunning: false,

    // toasts
    toasts: [],
    _toastId: 0,

    get hayFiltrosActivos() {
      const f = this.filtros;
      return !!(f.q || f.pais || f.nicho || f.ciudad || f.con_email || f.con_ig || f.sin_contactar);
    },

    get labelNicho() {
      return 'Nicho';
    },
    get labelCiudad() {
      return this.form.pais === 'BR' ? 'Cidade + estado' : 'Ciudad + provincia/estado';
    },

    async init() {
      await this.cargarCountries();
      await this.cargarLeads(1);
      await this.cargarBusquedas();
      await this.actualizarEnrichStatus();
      setInterval(() => this.actualizarEnrichStatus(), 1000);
    },

    flagFor(iso) {
      const p = this.countries.find((c) => c.iso === iso);
      return p ? p.flag : '';
    },

    toast(mensaje, tipo = 'info') {
      const id = ++this._toastId;
      this.toasts.push({ id, mensaje, tipo });
      setTimeout(() => {
        this.toasts = this.toasts.filter((t) => t.id !== id);
      }, 4000);
    },

    async _fetchJSON(url, options = {}) {
      const resp = await fetch(url, options);
      let data = null;
      try {
        data = await resp.json();
      } catch (e) {
        data = null;
      }
      if (!resp.ok) {
        const detail = (data && data.detail) || `Error ${resp.status}`;
        throw new Error(detail);
      }
      return data;
    },

    async cargarCountries() {
      try {
        this.countries = await this._fetchJSON('/api/countries');
      } catch (e) {
        this.toast('No se pudieron cargar los países: ' + e.message, 'error');
      }
    },

    async buscarNegocios() {
      if (!this.form.nicho || !this.form.ciudad) {
        this.toast('Completá nicho y ciudad para buscar', 'error');
        return;
      }
      this.buscando = true;
      this.avisoDuplicado = null;
      try {
        const data = await this._fetchJSON('/api/search', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(this.form),
        });
        this.avisoDuplicado = data.aviso_duplicado;
        this.toast(
          `Búsqueda completa: ${data.encontrados} encontrados, ${data.agregados} nuevos agregados (${data.duplicados} ya existían).`,
          'ok'
        );
        await this.cargarBusquedas();
        if (this.tab === 'leads') await this.cargarLeads(1);
      } catch (e) {
        this.toast('Error en la búsqueda: ' + e.message, 'error');
      } finally {
        this.buscando = false;
      }
    },

    _queryFiltros() {
      const params = new URLSearchParams();
      const f = this.filtros;
      if (f.q) params.set('q', f.q);
      if (f.pais) params.set('pais', f.pais);
      if (f.nicho) params.set('nicho', f.nicho);
      if (f.ciudad) params.set('ciudad', f.ciudad);
      if (f.con_email) params.set('con_email', 'true');
      if (f.con_ig) params.set('con_ig', 'true');
      if (f.sin_contactar) params.set('sin_contactar', 'true');
      return params;
    },

    async cargarLeads(page = 1) {
      if (page < 1) return;
      this.cargandoLeads = true;
      this.pagina = page;
      try {
        const params = this._queryFiltros();
        params.set('page', page);
        params.set('page_size', this.pageSize);
        const data = await this._fetchJSON(`/api/leads?${params.toString()}`);
        this.leads = data.items;
        this.totalLeads = data.total;
        this.seleccionados = [];
      } catch (e) {
        this.toast('Error cargando leads: ' + e.message, 'error');
      } finally {
        this.cargandoLeads = false;
      }
    },

    limpiarFiltros() {
      this.filtros = { q: '', pais: '', nicho: '', ciudad: '', con_email: false, con_ig: false, sin_contactar: false };
      this.cargarLeads(1);
    },

    toggleSeleccionarTodos(event) {
      this.seleccionados = event.target.checked ? this.leads.map((l) => l.id) : [];
    },

    async bulkAccion(accion, ids = null, tag = null) {
      const idsAccion = ids || this.seleccionados;
      if (!idsAccion.length) return;
      try {
        await this._fetchJSON('/api/leads/bulk', {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ids: idsAccion, accion, tag }),
        });
        this.toast(`Acción "${accion}" aplicada a ${idsAccion.length} lead(s).`, 'ok');
        await this.cargarLeads(this.pagina);
        if (this.panelLead && idsAccion.includes(this.panelLead.id)) {
          this.panelLead = null;
        }
      } catch (e) {
        this.toast('Error aplicando acción: ' + e.message, 'error');
      }
    },

    bulkTagPrompt() {
      const tag = window.prompt('Tag a agregar a los leads seleccionados:');
      if (tag && tag.trim()) {
        this.bulkAccion('tag', null, tag.trim());
      }
    },

    abrirPanel(lead) {
      this.panelLead = lead;
      this.panelTags = [...(lead.tags || [])];
      this.nuevoTag = '';
    },

    async guardarTags() {
      if (!this.panelLead) return;
      try {
        await this._fetchJSON(`/api/leads/${this.panelLead.id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ tags: this.panelTags }),
        });
        this.panelLead.tags = [...this.panelTags];
        const idx = this.leads.findIndex((l) => l.id === this.panelLead.id);
        if (idx !== -1) this.leads[idx].tags = [...this.panelTags];
        this.toast('Tags actualizados.', 'ok');
      } catch (e) {
        this.toast('Error guardando tags: ' + e.message, 'error');
      }
    },

    exportarCSV() {
      const params = this._queryFiltros();
      params.set('columnas', this.columnasExport.join(','));
      window.location.href = `/api/export?${params.toString()}`;
      this.exportOpen = false;
    },

    async cargarBusquedas() {
      try {
        this.busquedas = await this._fetchJSON('/api/busquedas');
      } catch (e) {
        this.toast('Error cargando historial de búsquedas: ' + e.message, 'error');
      }
    },

    async iniciarEnrichment() {
      try {
        await this._fetchJSON('/api/enrich/start', { method: 'POST' });
        this.toast('Enrichment iniciado.', 'info');
      } catch (e) {
        this.toast('Error iniciando enrichment: ' + e.message, 'error');
      }
    },

    async actualizarEnrichStatus() {
      try {
        const data = await this._fetchJSON('/api/enrich/status');
        this.enrichStatus = data;
        if (this._enrichWasRunning && !data.en_curso) {
          this.toast(
            `Enrichment terminado: ${data.encontrados} de ${data.total} leads enriquecidos.`,
            'ok'
          );
          if (this.tab === 'leads') await this.cargarLeads(this.pagina);
        }
        this._enrichWasRunning = data.en_curso;
      } catch (e) {
        // silencioso: no molestar con toasts en cada poll fallido
      }
    },
  };
}
