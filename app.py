with st.chat_message("assistant"):

    if not matched_rows and st.session_state.pending_rows is not None:
        matched_rows = st.session_state.pending_rows

    if matched_rows:
        if not cabins_found:
            st.session_state.pending_rows = matched_rows
        else:
            st.session_state.pending_rows = None

        results = []
        fallback_results = []
        airline_display_name = ""

        for row in matched_rows:
            val_text = str(row.get('Validity', ''))
            excl_text = str(row.get('Exclusions', 'None listed'))
            sheet_score = get_date_score(val_text)
            airline_display_name = str(row.get('Airlines Name', '')).upper()

            row_dict = row.to_dict()
            row_dict["Exclusions"] = excl_text

            # --- DATE FILTER ---
            is_valid = True
            if active_score:
                if not sheet_score:
                    is_valid = False
                elif sheet_score < active_score:
                    is_valid = False

            # --- CABIN FILTER ---
            if cabins_found:
                cabin_columns = ["First", "Bus", "Prem. eco", "Eco"]
                for col in cabin_columns:
                    if col not in cabins_found:
                        row_dict.pop(col, None)

                for cabin in cabins_found:
                    if cabin in row_dict:
                        val = row_dict.pop(cabin)
                        row_dict.pop(cabin.upper(), None)
                        row_dict[cabin.upper()] = val

            # --- STORE RESULTS ---
            if is_valid:
                results.append(row_dict)
            else:
                if sheet_score:
                    fallback_results.append((sheet_score, row_dict))

        # --- PRIMARY RESULT ---
        if results:
            final_df = pd.DataFrame(results)

            base_cols = ["Airlines", "Airlines Name", "IATA"] + \
                        ([c.upper() for c in cabins_found] if cabins_found else []) + \
                        ["Validity", "Exclusions"]

            remaining_cols = [c for c in final_df.columns if c not in set(base_cols) and c != "S.No"]
            final_df = final_df[base_cols + remaining_cols]

            final_reply = f"✅ Found {len(results)} valid deal(s) for **{airline_display_name}**."
            final_table = final_df

        # --- FALLBACK RESULT ---
        else:
            if fallback_results:
                # get closest future/past deal
                fallback_results.sort(key=lambda x: abs(x[0] - active_score))
                closest_score = fallback_results[0][0]

                closest_rows = [r for s, r in fallback_results if s == closest_score]
                final_df = pd.DataFrame(closest_rows)

                final_reply = (
                    f"❌ No deals available for given date.\n\n"
                    f"👉 Closest available deal(s) are shown below."
                )
                final_table = final_df
            else:
                final_reply = f"❌ No deals found for **{airline_display_name}**."
                final_table = None

        # --- DISPLAY ---
        st.markdown(final_reply)

        if final_table is not None:
            final_table = final_table.copy()
            final_table.columns = final_table.columns.astype(str).str.strip()
            final_table = final_table.loc[:, ~final_table.columns.duplicated()]
            st.dataframe(final_table, use_container_width=True)

        st.session_state.messages.append({
            "role": "assistant",
            "content": final_reply,
            "table": final_table
        })

    else:
        resp = "I couldn't find that airline. Please try 'AI', 'AA', etc."
        st.write(resp)
        st.session_state.messages.append({
            "role": "assistant",
            "content": resp,
            "table": None
        })
