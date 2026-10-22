// Generated from the frozen Gate 0 contract. Run npm run types:generate.
export interface paths {
    "/orders/parse-draft": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Parse a masked order message and create draft version 1
         * @description Allowed roles are CLERK and OWNER. The backend performs local PII masking before persistence or logging; raw message_text is request-scoped only.
         */
        post: operations["parseDraft"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/orders/drafts": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List drafts visible to the current tenant */
        get: operations["listDrafts"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/orders/drafts/{draft_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get the current draft aggregate */
        get: operations["getDraft"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/orders/drafts/{draft_id}/lines": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /**
         * Atomically replace editable lines, resolve message issues and create a version
         * @description Every existing line_id must appear exactly once in lines or deleted_line_ids. The service recalculates issues, prices, clarification, escalation and status.
         */
        put: operations["saveLines"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/orders/{draft_id}/approve": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Approve the latest saved version or create an owner approval request */
        post: operations["approve"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/approvals": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List approval work items visible to the current user
         * @description OWNER sees tenant approval work items and may use mine=true to filter to items personally submitted. CLERK is always server-filtered to requested_by=current_user, regardless of the mine value, and receives read-only items with allowed_actions=[]. WAREHOUSE is forbidden.
         */
        get: operations["listApprovals"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/approvals/{approval_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get immutable approval snapshot and allowed actions
         * @description OWNER may read any approval in the current tenant. CLERK may read only an item whose requested_by equals the current user; other items are returned as 404 and allowed_actions is empty. WAREHOUSE is forbidden.
         */
        get: operations["getApproval"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/approvals/{approval_id}/decide": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Approve or reject an owner approval request
         * @description OWNER only. REJECT requires a non-empty note.
         */
        post: operations["decideApproval"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/orders/{do_number}/audit-detail": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Compare AI initial snapshot with the approved delivery order */
        get: operations["getAuditDetail"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/activity": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List safe tenant activity events */
        get: operations["listActivity"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/me": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get identity, tenant, role and server-authoritative permissions */
        get: operations["getMe"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ai/status": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get AI endpoint readiness and current mode */
        get: operations["getAiStatus"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ai/wake": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Request AI warm-up
         * @description Allowed roles are CLERK and OWNER.
         */
        post: operations["wakeAi"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/customers": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List customers visible to CLERK/OWNER
         * @description P0 customer picker source. WAREHOUSE is forbidden. Phone is role-cropped.
         */
        get: operations["listCustomers"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/delivery-orders/{do_number}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Read a DO for CLERK/OWNER
         * @description P0 completion/refresh path. Requires CLERK or OWNER; WAREHOUSE must use the warehouse endpoint.
         */
        get: operations["getDeliveryOrder"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/warehouse/delivery-orders/{do_number}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Read a role-redacted DO for WAREHOUSE (P1 view binding)
         * @description P1 warehouse read endpoint; response schema has no price, phone, tier, raw message or AI fields.
         */
        get: operations["getWarehouseDeliveryOrder"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** @enum {string} */
        Role: "CLERK" | "OWNER" | "WAREHOUSE";
        /** @enum {string} */
        DraftStatus: "DISAMBIGUATION_REQUIRED" | "READY_FOR_APPROVAL" | "PENDING_OWNER_APPROVAL" | "DO_GENERATED" | "REJECTED";
        /** @enum {string} */
        TerminationReason: "OWNER_REJECTED" | "CLERK_DISCARDED" | "SYSTEM_TERMINATED";
        /** @enum {string} */
        IssueCode: "MULTIPLE_PACK_SIZES" | "MULTIPLE_GRADES" | "MISSING_UOM" | "LOW_CONFIDENCE_MATCH" | "INSUFFICIENT_STOCK" | "CUSTOMER_CONDITION" | "SAME_DAY_ORDER" | "UNUSUAL_QTY";
        /** @enum {string} */
        IssueReasonCode: "INVALID_QUANTITY" | "FIELD_NOT_EVIDENCED" | "FAMILY_NOT_EVIDENCED" | "DUPLICATE_SPAN" | "OVERLAPPING_SPAN" | "SOURCE_EVIDENCE_INVALID" | "UNKNOWN_PRODUCT" | "NO_CANDIDATE" | "LOW_SCORE" | "SMALL_SCORE_GAP" | "AMBIGUOUS_QUANTITY";
        /** @enum {string} */
        ConditionKind: "STOCK" | "PRICE" | "TIME" | "OTHER";
        /** @enum {string} */
        ConditionScope: "SINGLE_LINE" | "MULTI_LINE" | "ORDER_LEVEL" | "UNKNOWN";
        /** @enum {string} */
        AskWho: "CUSTOMER" | "OWNER" | "CLERK" | "SYSTEM";
        /** @enum {string} */
        ResolutionChoice: "CONFIRMED_WITH_CUSTOMER" | "ACCEPT_REQUESTED_PRICE" | "NOT_A_CONDITION" | "SEPARATE_ADD_ON" | "DUPLICATE" | "CHANGE_EXISTING";
        /** @enum {string} */
        EscalationCode: "PRICE_OVERRIDE_BELOW_TIER" | "AMOUNT_OVER_THRESHOLD" | "CUSTOMER_CREDIT_FLAG";
        /** @enum {string} */
        MatchSource: "SUGGESTED_DEFAULT" | "LLM_EXTRACTED" | "RAPIDFUZZ_FALLBACK" | "MANUAL_SELECTED";
        /** @enum {string} */
        AiMode: "LLM" | "FALLBACK" | "ALIAS_ONLY" | "MIXED";
        /** @enum {string} */
        PriceBasis: "UNIT" | "TOTAL" | "UNKNOWN";
        /** @enum {string} */
        ApprovalStatus: "PENDING" | "APPROVED" | "REJECTED";
        /** @enum {string} */
        ApprovalDecision: "APPROVE" | "REJECT";
        /** @enum {string} */
        AllowedAction: "EDIT_DRAFT" | "RESOLVE_ISSUE" | "COPY_CLARIFICATION" | "APPROVE_AND_GENERATE_DO" | "SUBMIT_FOR_OWNER" | "OWNER_APPROVE" | "OWNER_REJECT" | "CANCEL_DRAFT" | "VIEW_ACTIVITY" | "WAKE_AI";
        /** @enum {string} */
        CreditFlag: "NONE" | "OVERDUE_NOTICE";
        /** @enum {string} */
        AliasScope: "CUSTOMER" | "TENANT";
        /** @enum {string} */
        AiState: "OFFLINE" | "WARMING" | "READY" | "DEGRADED";
        /** @enum {string} */
        MaskToken: "[REDACTED_PHONE]" | "[REDACTED_MYKAD]" | "[REDACTED_EMAIL]";
        /** @enum {string} */
        ErrorCode: "DISAMBIGUATION_UNRESOLVED" | "INSUFFICIENT_STOCK" | "TARGET_LINE_REQUIRED" | "OVERRIDE_REQUIRED" | "NOTE_REQUIRED" | "EMPTY_ORDER" | "INVALID_LINE_OPERATION" | "INVALID_TOKEN" | "FORBIDDEN_ACTION" | "TENANT_MISMATCH" | "RESOURCE_NOT_FOUND" | "STALE_VERSION" | "PENDING_OWNER_APPROVAL" | "ALREADY_APPROVED" | "DRAFT_REJECTED" | "STOCK_CHANGED" | "REQUEST_VALIDATION_FAILED" | "MESSAGE_TOO_LONG" | "REJECTION_REASON_REQUIRED" | "INVALID_QUANTITY" | "MISSING_TIER_PRICE" | "RATE_LIMITED" | "AI_AND_FALLBACK_UNAVAILABLE";
        DecimalString: string;
        Error: {
            error_code: components["schemas"]["ErrorCode"];
            message: string;
            details: {
                [key: string]: unknown;
            };
        };
        SpanView: {
            text: string;
            start: number;
            end: number;
            normalizer_version: string;
        };
        FieldEvidence: {
            field: string;
            raw_text: string;
            start: number;
            end: number;
            normalizer_version: string;
        };
        WorkingLineInput: {
            line_id?: string | null;
            client_line_ref?: string | null;
            sku_id?: string | null;
            /** @description Optional on writes when sku_id determines family; responses use UNKNOWN, never null. */
            family_id?: string | null;
            confirmed_qty?: number | null;
            uom?: string | null;
            pack_size?: string | null;
            grade?: string | null;
            unit_price_override?: components["schemas"]["DecimalString"] | null;
            override_reason?: string | null;
            match_source: components["schemas"]["MatchSource"];
            /** @default false */
            save_to_alias_cache?: boolean;
            /** @default CUSTOMER */
            alias_scope?: components["schemas"]["AliasScope"];
        } & ({
            line_id: string | null;
        } | {
            client_line_ref: string | null;
        });
        WorkingLine: {
            line_id: string;
            client_line_ref?: string | null;
            sku_id?: string | null;
            family_id: string;
            description?: string | null;
            readonly requested_qty: number;
            confirmed_qty?: number | null;
            readonly effective_qty: number;
            uom?: string | null;
            pack_size?: string | null;
            grade?: string | null;
            readonly tier_unit_price?: components["schemas"]["DecimalString"] | null;
            unit_price_override?: components["schemas"]["DecimalString"] | null;
            override_reason?: string | null;
            readonly effective_unit_price?: components["schemas"]["DecimalString"] | null;
            readonly subtotal_rm?: components["schemas"]["DecimalString"] | null;
            match_source: components["schemas"]["MatchSource"];
            /** @description Masked source text for display and fallback when offsets are invalid. */
            source_span?: string | null;
            readonly span_start?: number | null;
            readonly span_end?: number | null;
            readonly field_evidence: components["schemas"]["FieldEvidence"][];
            /** @description Stable candidate list for unresolved/low-confidence lines; empty when the line is already resolved. */
            readonly candidate_skus: components["schemas"]["SkuCandidate"][];
            /** @description Alias created by a previous save for this line, so the checkbox can be restored after refresh. */
            readonly saved_alias?: components["schemas"]["AliasRecord"] | null;
            /** @description Inventory for the currently selected sku_id; null when no sku is selected. Distinct from candidate_skus[].available_qty. */
            readonly available_qty: number | null;
        };
        Issue: {
            issue_id: string;
            code: components["schemas"]["IssueCode"];
            /** @description Required for CUSTOMER_CONDITION; null for non-condition issues. Deterministically derived as CND_ plus the first 24 uppercase hexadecimal characters of SHA-256(UTF-8(draft_id|condition_kind|span_start|span_end)). */
            condition_id?: string | null;
            line_id?: string | null;
            /** @description Canonical masked source text. */
            span?: string | null;
            /**
             * @deprecated
             * @description Derived compatibility alias of span; remove after the v1.3 frontend migration.
             */
            readonly source_span?: string | null;
            span_start?: number | null;
            span_end?: number | null;
            condition_kind?: components["schemas"]["ConditionKind"] | null;
            condition_scope?: components["schemas"]["ConditionScope"] | null;
            candidate_line_ids: string[];
            target_line_ids: string[];
            requested_unit_price?: components["schemas"]["DecimalString"] | null;
            price_basis?: components["schemas"]["PriceBasis"] | null;
            reason_code?: components["schemas"]["IssueReasonCode"] | null;
            ask: components["schemas"]["AskWho"];
            data_used: {
                [key: string]: unknown;
            };
            blocking: boolean;
            resolved: boolean;
            resolution?: components["schemas"]["ResolutionChoice"] | null;
            resolution_note?: string | null;
            /** @enum {string|null} */
            auto_resolved_by?: "STOCK_CHECK" | null;
        } & unknown;
        IssueResolution: {
            issue_id: string;
            choice: components["schemas"]["ResolutionChoice"];
            target_line_ids: string[];
            confirmed_unit_price?: components["schemas"]["DecimalString"] | null;
            price_basis?: components["schemas"]["PriceBasis"] | null;
            note?: string | null;
        };
        SaveLinesRequest: {
            expected_version: number;
            lines: components["schemas"]["WorkingLineInput"][];
            /** @default [] */
            deleted_line_ids?: string[];
            /** @default [] */
            resolutions?: components["schemas"]["IssueResolution"][];
        };
        ParseDraftRequest: {
            customer_id: string;
            /** @description Raw pasted message. The backend masks PII before logging or persistence. */
            message_text: string;
            language_hint?: string | null;
        };
        ClarificationDraft: {
            language: string;
            message: string;
            unresolved_issue_ids: string[];
        };
        CustomerSummary: {
            customer_id: string;
            name: string;
            tier: string;
            credit_flag: components["schemas"]["CreditFlag"];
            readonly has_credit_notice: boolean;
            /** @description Omitted or null in role-redacted responses. */
            phone_e164?: string | null;
        };
        OrderTotals: {
            order_total: components["schemas"]["DecimalString"] | null;
            /** @constant */
            currency: "MYR";
            is_complete: boolean;
        };
        TenantSummary: {
            id: string;
            name: string;
        };
        OrderDraft: {
            draft_id: string;
            version: number;
            status: components["schemas"]["DraftStatus"];
            customer_id: string;
            customer: components["schemas"]["CustomerSummary"];
            /** @description Backend-masked message; raw message_text is never returned or persisted. */
            masked_message: string;
            ai_mode: components["schemas"]["AiMode"];
            lines: components["schemas"]["WorkingLine"][];
            issues: components["schemas"]["Issue"][];
            /** @description Derived CUSTOMER_CONDITION subset of issues for direct UI rendering. */
            readonly conditions: components["schemas"]["Issue"][];
            blocking_issues: components["schemas"]["IssueCode"][];
            escalation_preview: components["schemas"]["EscalationReason"][];
            totals: components["schemas"]["OrderTotals"];
            allowed_actions: components["schemas"]["AllowedAction"][];
            blocked_actions: {
                [key: string]: string[];
            };
            clarification_draft?: components["schemas"]["ClarificationDraft"] | null;
            clarification_lang?: string | null;
            ignored_spans: components["schemas"]["SpanView"][];
            /** @deprecated */
            readonly disambiguations?: components["schemas"]["Issue"][];
            termination_reason?: components["schemas"]["TerminationReason"] | null;
            terminated_by_user_id?: string | null;
            termination_note?: string | null;
            /** Format: date-time */
            created_at: string;
            /** Format: date-time */
            updated_at: string;
            /** @description DO number when status is DO_GENERATED; null otherwise. */
            readonly do_number?: string | null;
        };
        DraftSummary: {
            draft_id: string;
            version: number;
            status: components["schemas"]["DraftStatus"];
            customer_id: string;
            customer_name: string;
            /** @description Masked and length-limited preview. */
            message_preview: string;
            blocking_issues: components["schemas"]["IssueCode"][];
            open_blocking_issue_count: number;
            owner_escalation_count: number;
            extraction_sources: components["schemas"]["MatchSource"][];
            allowed_actions: components["schemas"]["AllowedAction"][];
            /** Format: date-time */
            updated_at: string;
            /** @description DO number when status is DO_GENERATED; null otherwise. */
            readonly do_number?: string | null;
        };
        DraftListResponse: {
            items: components["schemas"]["DraftSummary"][];
            next_cursor?: string | null;
        };
        ApproveRequest: {
            expected_version: number;
            /**
             * @deprecated
             * @description Compatibility only; atomically save a new version before approving it.
             */
            confirmed_items?: components["schemas"]["WorkingLineInput"][];
        };
        EscalationReason: {
            code: components["schemas"]["EscalationCode"];
            line_id?: string | null;
            detail: {
                [key: string]: unknown;
            };
        };
        ApprovalRequest: {
            approval_id: string;
            draft_id: string;
            draft_version: number;
            status: components["schemas"]["ApprovalStatus"];
            customer: components["schemas"]["CustomerSummary"];
            total_rm: components["schemas"]["DecimalString"];
            line_count: number;
            reasons: components["schemas"]["EscalationReason"][];
            requested_by: string;
            /** Format: date-time */
            requested_at: string;
            allowed_actions: components["schemas"]["AllowedAction"][];
            decided_by?: string | null;
            /** Format: date-time */
            decided_at?: string | null;
            decision_note?: string | null;
        };
        ApprovalSnapshot: {
            customer_id: string;
            customer_name: string;
            masked_customer_text: string;
            lines: components["schemas"]["WorkingLine"][];
            total_rm: components["schemas"]["DecimalString"];
            reasons: components["schemas"]["EscalationReason"][];
        };
        FieldDiff: {
            draft_version: number;
            line_id?: string | null;
            /** @description Field path relative to line_id when line_id is present (e.g. unit_price_override); otherwise relative to the draft/DO root. Do not use array indexes. */
            field_path: string;
            before_value?: unknown;
            after_value?: unknown;
            source: string;
            reason_code: string;
        };
        StockCheckSummary: {
            /** @enum {string} */
            state: "NOT_RUN" | "PASSED" | "FAILED";
            /** Format: date-time */
            checked_at: string | null;
            lines: {
                line_id: string;
                sku_id: string;
                requested_qty: number;
                available_qty: number;
                sufficient: boolean;
                effective_qty: number;
            }[];
        };
        ApprovalDetail: {
            approval_id: string;
            draft_id: string;
            draft_version: number;
            status: components["schemas"]["ApprovalStatus"];
            customer: components["schemas"]["CustomerSummary"];
            total_rm: components["schemas"]["DecimalString"];
            line_count: number;
            reasons: components["schemas"]["EscalationReason"][];
            requested_by: string;
            /** Format: date-time */
            requested_at: string;
            allowed_actions: components["schemas"]["AllowedAction"][];
            decided_by?: string | null;
            /** Format: date-time */
            decided_at?: string | null;
            decision_note?: string | null;
            snapshot: components["schemas"]["ApprovalSnapshot"];
            field_diffs: components["schemas"]["FieldDiff"][];
            stock_check: components["schemas"]["StockCheckSummary"];
        };
        ApprovalListResponse: {
            items: components["schemas"]["ApprovalRequest"][];
            next_cursor?: string | null;
        };
        DecideRequest: {
            decision: components["schemas"]["ApprovalDecision"];
            note?: string | null;
        };
        ApprovalDecisionResult: {
            approval_id: string;
            draft_id: string;
            /** @constant */
            status: "REJECTED";
            /** @constant */
            termination_reason: "OWNER_REJECTED";
            decided_by: string;
            /** Format: date-time */
            decided_at: string;
            decision_note?: string;
        };
        ReplyDraft: {
            language: string;
            message: string;
            do_number: string;
            warnings: string[];
        };
        DeliveryOrderLine: {
            line_id: string;
            sku_id: string;
            display_name: string;
            quantity: number;
            unit: string;
            tier_unit_price: components["schemas"]["DecimalString"];
            applied_unit_price: components["schemas"]["DecimalString"];
            subtotal_rm: components["schemas"]["DecimalString"];
            override_reason?: string | null;
            picking_note?: string | null;
        };
        WarehouseDeliveryOrderItem: {
            sku_id: string;
            display_name: string;
            quantity: number;
            unit: string;
            picking_note?: string | null;
        };
        /** @description Role-redacted WAREHOUSE view; price, tier, phone, raw message and AI fields are forbidden. */
        WarehouseDeliveryOrder: {
            do_number: string;
            customer_name: string;
            items: components["schemas"]["WarehouseDeliveryOrderItem"][];
            /** Format: date-time */
            approved_at: string;
        };
        DeliveryOrder: {
            do_number: string;
            draft_id: string;
            draft_version: number;
            customer_id: string;
            customer_name: string;
            lines: components["schemas"]["DeliveryOrderLine"][];
            final_total_rm: components["schemas"]["DecimalString"];
            prepared_by: string;
            approved_by: string;
            escalation_reasons: components["schemas"]["EscalationReason"][];
            /** @enum {string} */
            approval_mode: "DIRECT" | "OWNER_APPROVED" | "OWNER_SELF_APPROVED";
            reply_draft: components["schemas"]["ReplyDraft"];
            related_do_number?: string | null;
            /** Format: date-time */
            approved_at: string;
        };
        AuditEvent: {
            event_type: string;
            actor_user_id: string | null;
            actor_role: components["schemas"]["Role"] | null;
            /** Format: date-time */
            created_at: string;
            payload: {
                [key: string]: unknown;
            };
        };
        AuditDetail: {
            do_number: string;
            draft_id: string;
            draft_version: number;
            ai_initial_snapshot: {
                [key: string]: unknown;
            };
            final_snapshot: components["schemas"]["DeliveryOrder"];
            field_diffs: components["schemas"]["FieldDiff"][];
            events: components["schemas"]["AuditEvent"][];
        };
        ActivityItem: {
            activity_id: number;
            entity_id?: string | null;
            event_type: string;
            payload: {
                [key: string]: unknown;
            };
            actor_user_id?: string | null;
            actor_role: components["schemas"]["Role"] | null;
            /** Format: date-time */
            created_at: string;
        };
        ActivityListResponse: {
            items: components["schemas"]["ActivityItem"][];
            next_cursor?: string | null;
        };
        MeResponse: {
            user_id: string;
            tenant: components["schemas"]["TenantSummary"];
            display_name: string;
            role: components["schemas"]["Role"];
            permissions: components["schemas"]["AllowedAction"][];
            permission_summary: string;
        };
        AiStatus: {
            state: components["schemas"]["AiState"];
            available_modes: components["schemas"]["AiMode"][];
            fallback_available: boolean;
            /** Format: date-time */
            last_checked_at: string;
            message: string;
        };
        AiWakeResult: {
            state: components["schemas"]["AiState"];
            accepted: boolean;
            fallback_available: boolean;
            /** Format: date-time */
            last_checked_at: string;
            message: string;
        };
        SkuCandidate: {
            sku_id: string;
            family_id: string;
            display_name: string;
            pack_size?: string | null;
            grade?: string | null;
            base_unit: string;
            tier_unit_price: components["schemas"]["DecimalString"];
            available_qty: number;
        };
        AliasRecord: {
            alias_id: string;
            phrase: string;
            /** @enum {string} */
            target_type: "FAMILY" | "SKU";
            family_id?: string | null;
            product_id?: string | null;
            scope: components["schemas"]["AliasScope"];
            active: boolean;
            /** Format: date-time */
            created_at: string;
        };
        CustomerListResponse: {
            items: components["schemas"]["CustomerSummary"][];
            next_cursor?: string | null;
        };
    };
    responses: {
        /** @description Current draft aggregate. */
        OrderDraftResponse: {
            headers: {
                "X-Request-ID": components["headers"]["X-Request-ID"];
                [name: string]: unknown;
            };
            content: {
                "application/json": components["schemas"]["OrderDraft"];
            };
        };
        /** @description Paginated drafts. */
        DraftListResponse: {
            headers: {
                "X-Request-ID": components["headers"]["X-Request-ID"];
                [name: string]: unknown;
            };
            content: {
                "application/json": components["schemas"]["DraftListResponse"];
            };
        };
        /** @description Approved immutable delivery order. */
        DeliveryOrderResponse: {
            headers: {
                "X-Request-ID": components["headers"]["X-Request-ID"];
                [name: string]: unknown;
            };
            content: {
                "application/json": components["schemas"]["DeliveryOrder"];
            };
        };
        /** @description Owner approval request created or returned. */
        ApprovalRequestResponse: {
            headers: {
                "X-Request-ID": components["headers"]["X-Request-ID"];
                [name: string]: unknown;
            };
            content: {
                "application/json": components["schemas"]["ApprovalRequest"];
            };
        };
        /** @description Paginated owner approval work items. */
        ApprovalListResponse: {
            headers: {
                "X-Request-ID": components["headers"]["X-Request-ID"];
                [name: string]: unknown;
            };
            content: {
                "application/json": components["schemas"]["ApprovalListResponse"];
            };
        };
        /** @description Approval item with immutable snapshot and diffs. */
        ApprovalDetailResponse: {
            headers: {
                "X-Request-ID": components["headers"]["X-Request-ID"];
                [name: string]: unknown;
            };
            content: {
                "application/json": components["schemas"]["ApprovalDetail"];
            };
        };
        /** @description APPROVE returns a delivery order; REJECT returns a rejection result. */
        DecisionResponse: {
            headers: {
                "X-Request-ID": components["headers"]["X-Request-ID"];
                [name: string]: unknown;
            };
            content: {
                "application/json": components["schemas"]["DeliveryOrder"] | components["schemas"]["ApprovalDecisionResult"];
            };
        };
        /** @description Immutable approved audit detail. */
        AuditDetailResponse: {
            headers: {
                "X-Request-ID": components["headers"]["X-Request-ID"];
                [name: string]: unknown;
            };
            content: {
                "application/json": components["schemas"]["AuditDetail"];
            };
        };
        /** @description Paginated activity events. */
        ActivityListResponse: {
            headers: {
                "X-Request-ID": components["headers"]["X-Request-ID"];
                [name: string]: unknown;
            };
            content: {
                "application/json": components["schemas"]["ActivityListResponse"];
            };
        };
        /** @description Authenticated principal and permissions. */
        MeResponse: {
            headers: {
                "X-Request-ID": components["headers"]["X-Request-ID"];
                [name: string]: unknown;
            };
            content: {
                "application/json": components["schemas"]["MeResponse"];
            };
        };
        /** @description AI readiness state. */
        AiStatusResponse: {
            headers: {
                "X-Request-ID": components["headers"]["X-Request-ID"];
                [name: string]: unknown;
            };
            content: {
                "application/json": components["schemas"]["AiStatus"];
            };
        };
        /** @description AI wake request state. */
        AiWakeResponse: {
            headers: {
                "X-Request-ID": components["headers"]["X-Request-ID"];
                [name: string]: unknown;
            };
            content: {
                "application/json": components["schemas"]["AiWakeResult"];
            };
        };
        /** @description Business validation failed. */
        BadRequestError: {
            headers: {
                "X-Request-ID": components["headers"]["X-Request-ID"];
                [name: string]: unknown;
            };
            content: {
                "application/json": components["schemas"]["Error"];
            };
        };
        /** @description Missing, expired or invalid bearer token. */
        UnauthorizedError: {
            headers: {
                "X-Request-ID": components["headers"]["X-Request-ID"];
                [name: string]: unknown;
            };
            content: {
                "application/json": components["schemas"]["Error"];
            };
        };
        /** @description Authenticated but action is forbidden or tenant mismatch was supplied. */
        ForbiddenError: {
            headers: {
                "X-Request-ID": components["headers"]["X-Request-ID"];
                [name: string]: unknown;
            };
            content: {
                "application/json": components["schemas"]["Error"];
            };
        };
        /** @description Resource does not exist in the current tenant view. */
        NotFoundError: {
            headers: {
                "X-Request-ID": components["headers"]["X-Request-ID"];
                [name: string]: unknown;
            };
            content: {
                "application/json": components["schemas"]["Error"];
            };
        };
        /** @description Resource state or optimistic version conflict. */
        ConflictError: {
            headers: {
                "X-Request-ID": components["headers"]["X-Request-ID"];
                [name: string]: unknown;
            };
            content: {
                "application/json": components["schemas"]["Error"];
            };
        };
        /** @description Request shape, field value or required configuration is invalid. */
        ValidationError: {
            headers: {
                "X-Request-ID": components["headers"]["X-Request-ID"];
                [name: string]: unknown;
            };
            content: {
                "application/json": components["schemas"]["Error"];
            };
        };
        /** @description Parse or AI wake rate limit exceeded. */
        RateLimitedError: {
            headers: {
                "X-Request-ID": components["headers"]["X-Request-ID"];
                "Retry-After": components["headers"]["Retry-After"];
                [name: string]: unknown;
            };
            content: {
                "application/json": components["schemas"]["Error"];
            };
        };
        /** @description AI and safe fallback are both unavailable. */
        UnavailableError: {
            headers: {
                "X-Request-ID": components["headers"]["X-Request-ID"];
                [name: string]: unknown;
            };
            content: {
                "application/json": components["schemas"]["Error"];
            };
        };
        /** @description Customers visible in the current tenant; phone is role-cropped. */
        CustomerListResponse: {
            headers: {
                "X-Request-ID": components["headers"]["X-Request-ID"];
                [name: string]: unknown;
            };
            content: {
                "application/json": components["schemas"]["CustomerListResponse"];
            };
        };
        /** @description Warehouse-facing DO with price, phone, tier and raw message removed. */
        WarehouseDeliveryOrderResponse: {
            headers: {
                "X-Request-ID": components["headers"]["X-Request-ID"];
                [name: string]: unknown;
            };
            content: {
                "application/json": components["schemas"]["WarehouseDeliveryOrder"];
            };
        };
    };
    parameters: {
        DraftId: string;
        ApprovalId: string;
        DoNumber: string;
        Limit: number;
        Cursor: string;
        DraftStatusQuery: components["schemas"]["DraftStatus"];
        ApprovalStatusQuery: components["schemas"]["ApprovalStatus"];
        /** @description OWNER optional self-submission filter. CLERK is always restricted to self-submitted approvals even when this parameter is omitted or false. */
        Mine: boolean;
    };
    requestBodies: never;
    headers: {
        /** @description Correlation identifier returned on every response. */
        "X-Request-ID": string;
        /** @description Seconds until the request may be retried. */
        "Retry-After": number;
    };
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    parseDraft: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ParseDraftRequest"];
            };
        };
        responses: {
            200: components["responses"]["OrderDraftResponse"];
            401: components["responses"]["UnauthorizedError"];
            403: components["responses"]["ForbiddenError"];
            422: components["responses"]["ValidationError"];
            429: components["responses"]["RateLimitedError"];
            503: components["responses"]["UnavailableError"];
        };
    };
    listDrafts: {
        parameters: {
            query?: {
                status?: components["parameters"]["DraftStatusQuery"];
                limit?: components["parameters"]["Limit"];
                cursor?: components["parameters"]["Cursor"];
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: components["responses"]["DraftListResponse"];
            401: components["responses"]["UnauthorizedError"];
            403: components["responses"]["ForbiddenError"];
            422: components["responses"]["ValidationError"];
        };
    };
    getDraft: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                draft_id: components["parameters"]["DraftId"];
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: components["responses"]["OrderDraftResponse"];
            401: components["responses"]["UnauthorizedError"];
            403: components["responses"]["ForbiddenError"];
            404: components["responses"]["NotFoundError"];
        };
    };
    saveLines: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                draft_id: components["parameters"]["DraftId"];
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SaveLinesRequest"];
            };
        };
        responses: {
            200: components["responses"]["OrderDraftResponse"];
            400: components["responses"]["BadRequestError"];
            401: components["responses"]["UnauthorizedError"];
            403: components["responses"]["ForbiddenError"];
            404: components["responses"]["NotFoundError"];
            409: components["responses"]["ConflictError"];
            422: components["responses"]["ValidationError"];
        };
    };
    approve: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                draft_id: components["parameters"]["DraftId"];
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ApproveRequest"];
            };
        };
        responses: {
            200: components["responses"]["DeliveryOrderResponse"];
            202: components["responses"]["ApprovalRequestResponse"];
            400: components["responses"]["BadRequestError"];
            401: components["responses"]["UnauthorizedError"];
            403: components["responses"]["ForbiddenError"];
            404: components["responses"]["NotFoundError"];
            409: components["responses"]["ConflictError"];
            422: components["responses"]["ValidationError"];
        };
    };
    listApprovals: {
        parameters: {
            query?: {
                status?: components["parameters"]["ApprovalStatusQuery"];
                /** @description OWNER optional self-submission filter. CLERK is always restricted to self-submitted approvals even when this parameter is omitted or false. */
                mine?: components["parameters"]["Mine"];
                limit?: components["parameters"]["Limit"];
                cursor?: components["parameters"]["Cursor"];
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: components["responses"]["ApprovalListResponse"];
            401: components["responses"]["UnauthorizedError"];
            403: components["responses"]["ForbiddenError"];
            422: components["responses"]["ValidationError"];
        };
    };
    getApproval: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                approval_id: components["parameters"]["ApprovalId"];
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: components["responses"]["ApprovalDetailResponse"];
            401: components["responses"]["UnauthorizedError"];
            403: components["responses"]["ForbiddenError"];
            404: components["responses"]["NotFoundError"];
        };
    };
    decideApproval: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                approval_id: components["parameters"]["ApprovalId"];
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DecideRequest"];
            };
        };
        responses: {
            200: components["responses"]["DecisionResponse"];
            400: components["responses"]["BadRequestError"];
            401: components["responses"]["UnauthorizedError"];
            403: components["responses"]["ForbiddenError"];
            404: components["responses"]["NotFoundError"];
            409: components["responses"]["ConflictError"];
            422: components["responses"]["ValidationError"];
        };
    };
    getAuditDetail: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                do_number: components["parameters"]["DoNumber"];
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: components["responses"]["AuditDetailResponse"];
            401: components["responses"]["UnauthorizedError"];
            403: components["responses"]["ForbiddenError"];
            404: components["responses"]["NotFoundError"];
        };
    };
    listActivity: {
        parameters: {
            query?: {
                entity_id?: string;
                limit?: components["parameters"]["Limit"];
                cursor?: components["parameters"]["Cursor"];
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: components["responses"]["ActivityListResponse"];
            401: components["responses"]["UnauthorizedError"];
            403: components["responses"]["ForbiddenError"];
            422: components["responses"]["ValidationError"];
        };
    };
    getMe: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: components["responses"]["MeResponse"];
            401: components["responses"]["UnauthorizedError"];
        };
    };
    getAiStatus: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: components["responses"]["AiStatusResponse"];
            401: components["responses"]["UnauthorizedError"];
        };
    };
    wakeAi: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: components["responses"]["AiWakeResponse"];
            401: components["responses"]["UnauthorizedError"];
            403: components["responses"]["ForbiddenError"];
            429: components["responses"]["RateLimitedError"];
            503: components["responses"]["UnavailableError"];
        };
    };
    listCustomers: {
        parameters: {
            query?: {
                limit?: components["parameters"]["Limit"];
                cursor?: components["parameters"]["Cursor"];
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: components["responses"]["CustomerListResponse"];
            401: components["responses"]["UnauthorizedError"];
            403: components["responses"]["ForbiddenError"];
            422: components["responses"]["ValidationError"];
        };
    };
    getDeliveryOrder: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                do_number: components["parameters"]["DoNumber"];
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: components["responses"]["DeliveryOrderResponse"];
            401: components["responses"]["UnauthorizedError"];
            403: components["responses"]["ForbiddenError"];
            404: components["responses"]["NotFoundError"];
        };
    };
    getWarehouseDeliveryOrder: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                do_number: components["parameters"]["DoNumber"];
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: components["responses"]["WarehouseDeliveryOrderResponse"];
            401: components["responses"]["UnauthorizedError"];
            403: components["responses"]["ForbiddenError"];
            404: components["responses"]["NotFoundError"];
        };
    };
}
