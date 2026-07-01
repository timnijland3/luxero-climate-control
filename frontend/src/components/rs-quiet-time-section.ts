import { LitElement, html, css } from "lit";
import { customElement, property } from "lit/decorators.js";
import type { HomeAssistant, FanConfig } from "../types";
import { localize } from "../utils/localize";
import { inputStyles } from "../styles/input-styles";
import "./shared/rs-threshold-field";

const ICON_CLOSE =
  "M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z";

@customElement("rs-quiet-time-section")
export class RsQuietTimeSection extends LitElement {
  @property({ attribute: false }) public hass!: HomeAssistant;
  @property({ attribute: false }) public fans: FanConfig[] = [];
  @property({ type: String }) public quietScheduleEntity = "";
  @property({ type: Boolean }) public editing = false;

  static styles = [
    inputStyles,
    css`
      :host {
        display: block;
      }

      .no-items {
        color: var(--secondary-text-color);
        font-size: 0.9em;
        margin: 0;
      }

      .schedule-row {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 6px 0;
        font-size: 14px;
      }

      .schedule-name {
        flex: 1;
        min-width: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .badge {
        font-size: 10px;
        font-weight: 500;
        padding: 1px 7px;
        border-radius: 8px;
        text-transform: uppercase;
        letter-spacing: 0.3px;
        flex-shrink: 0;
      }
      .badge.active {
        background: rgba(76, 175, 80, 0.15);
        color: #2e7d32;
      }
      .badge.inactive {
        background: rgba(0, 0, 0, 0.05);
        color: var(--secondary-text-color);
      }

      .form-label {
        display: block;
        font-size: 13px;
        font-weight: 500;
        color: var(--secondary-text-color);
        margin-bottom: 6px;
        text-transform: uppercase;
        letter-spacing: 0.3px;
      }

      ha-entity-picker {
        width: 100%;
      }

      .fan-list {
        display: flex;
        flex-direction: column;
        gap: 8px;
        margin: 12px 0;
      }

      .fan-row {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 6px 0;
      }

      .fan-name {
        flex: 1;
        min-width: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        font-size: 14px;
      }

      .fan-percent {
        flex-shrink: 0;
        font-weight: 500;
      }

      .fan-row rs-threshold-field {
        width: 140px;
        flex-shrink: 0;
      }

      .fan-row ha-icon-button {
        --mdc-icon-button-size: 28px;
        --mdc-icon-size: 16px;
        flex-shrink: 0;
      }

      .section-hint {
        font-size: 12px;
        color: var(--secondary-text-color);
        line-height: 1.5;
        margin: 8px 0 0;
      }

      .add-row {
        margin-top: 8px;
      }
    `,
  ];

  render() {
    return this.editing ? this._renderEdit() : this._renderView();
  }

  private _isQuietTimeActive(): boolean {
    if (!this.quietScheduleEntity) return false;
    return this.hass?.states?.[this.quietScheduleEntity]?.state === "on";
  }

  private _friendlyName(entityId: string): string {
    return (this.hass?.states?.[entityId]?.attributes?.friendly_name as string) || entityId;
  }

  private _renderView() {
    const l = this.hass.language;
    if (!this.quietScheduleEntity || this.fans.length === 0) {
      return html`<p class="no-items">${localize("quiet_time.no_schedule", l)}</p>`;
    }
    const active = this._isQuietTimeActive();
    return html`
      <div class="schedule-row">
        <span class="schedule-name">${this._friendlyName(this.quietScheduleEntity)}</span>
        <span class="badge ${active ? "active" : "inactive"}">
          ${active ? localize("quiet_time.active", l) : localize("quiet_time.inactive", l)}
        </span>
      </div>
      ${this.fans.map(
        (fan) => html`
          <div class="fan-row">
            <span class="fan-name">${this._friendlyName(fan.entity_id)}</span>
            <span class="fan-percent">${fan.quiet_max_percent}%</span>
          </div>
        `,
      )}
    `;
  }

  private _entityFilter = (entity: { entity_id: string }): boolean => {
    const id = entity.entity_id;
    if (id.split(".", 2)[1]?.startsWith("roommind_")) return false;
    return id.startsWith("fan.") && !this.fans.some((f) => f.entity_id === id);
  };

  private _renderEdit() {
    const l = this.hass.language;
    return html`
      <label class="form-label">${localize("quiet_time.schedule_label", l)}</label>
      <ha-entity-picker
        .hass=${this.hass}
        .value=${this.quietScheduleEntity}
        .includeDomains=${["schedule"]}
        allow-custom-entity
        @value-changed=${this._onScheduleChanged}
      ></ha-entity-picker>
      <div class="section-hint">${localize("quiet_time.schedule_hint", l)}</div>

      <label class="form-label" style="margin-top:16px">${localize("quiet_time.fans_label", l)}</label>
      ${this.fans.length === 0
        ? html`<p class="no-items">${localize("quiet_time.no_fans", l)}</p>`
        : html`
            <div class="fan-list">
              ${this.fans.map(
                (fan) => html`
                  <div class="fan-row">
                    <span class="fan-name">${this._friendlyName(fan.entity_id)}</span>
                    <rs-threshold-field
                      .value=${fan.quiet_max_percent}
                      .min=${0}
                      .max=${100}
                      .step=${5}
                      suffix="%"
                      @value-changed=${(e: CustomEvent<number>) =>
                        this._updateFanPercent(fan.entity_id, e.detail)}
                    ></rs-threshold-field>
                    <ha-icon-button
                      .path=${ICON_CLOSE}
                      @click=${() => this._removeFan(fan.entity_id)}
                    ></ha-icon-button>
                  </div>
                `,
              )}
            </div>
          `}
      <div class="add-row">
        <ha-entity-picker
          .hass=${this.hass}
          .includeDomains=${["fan"]}
          .entityFilter=${this._entityFilter}
          .value=${""}
          .label=${localize("quiet_time.add_fan", l)}
          @value-changed=${this._onFanPicked}
        ></ha-entity-picker>
      </div>
    `;
  }

  private _onScheduleChanged(e: CustomEvent<{ value: string }>) {
    e.stopPropagation();
    this._emit("quiet_schedule_entity", e.detail?.value ?? "");
  }

  private _onFanPicked(e: CustomEvent<{ value: string }>) {
    e.stopPropagation();
    const eid = e.detail?.value;
    if (!eid) return;
    this._emit("fans", [...this.fans, { entity_id: eid, quiet_max_percent: 30 }]);
    const picker = e.target as HTMLElement & { value: string };
    picker.value = "";
  }

  private _removeFan(entityId: string) {
    this._emit(
      "fans",
      this.fans.filter((f) => f.entity_id !== entityId),
    );
  }

  private _updateFanPercent(entityId: string, value: number) {
    this._emit(
      "fans",
      this.fans.map((f) => (f.entity_id === entityId ? { ...f, quiet_max_percent: value } : f)),
    );
  }

  private _emit(key: string, value: unknown) {
    this.dispatchEvent(
      new CustomEvent("setting-changed", {
        detail: { key, value },
        bubbles: true,
        composed: true,
      }),
    );
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "rs-quiet-time-section": RsQuietTimeSection;
  }
}
