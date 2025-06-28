# Testing Checklist for WRCPilot01 Golden Copy

## Pre-Deployment Testing ✅

### 1. Container Build & Start
- [ ] Docker image builds successfully: `docker build -t wrcbot:0.7 .`
- [ ] Container starts without errors: `docker run -d --name test_bot wrcbot:0.7`
- [ ] All plugins load correctly (check logs)
- [ ] Bot connects to Slack successfully

### 2. Plugin Loading Verification
Check logs for these confirmations:
- [ ] `SimpleNameCollector plugin activated with names storage`
- [ ] `MyPriorLife plugin activated with prior lives storage`
- [ ] `Extension activated - blocks support available via helper methods`
- [ ] No error messages during plugin activation

### 3. Basic Command Testing
- [ ] `@bot alive` - Should respond with "I'm alive!"
- [ ] `@bot help` - Should show available commands
- [ ] Bot responds to mentions correctly

### 4. SimpleNameCollector Plugin Testing
- [ ] **Step 1:** `@bot collect_name`
  - [ ] Shows introduction message
  - [ ] Displays interactive form with name input field
  - [ ] Has "Submit Name" and "Cancel" buttons
  
- [ ] **Step 2:** Fill form and click "Submit Name"
  - [ ] Shows success message with green checkmark
  - [ ] Confirms name was stored
  - [ ] Shows total count of names
  
- [ ] **Step 3:** `@bot names_list`
  - [ ] Shows collected names
  - [ ] Displays proper formatting
  
- [ ] **Step 4:** Test validation
  - [ ] Submit empty form - should show error
  - [ ] Submit same name again - should update existing

### 5. MyPriorLife Plugin Testing ⭐ (Previously Broken, Now Fixed)
- [ ] **Step 1:** `@bot mypriorlife`
  - [ ] Shows "In My Prior Life I was a Cat ! Now I am a Bot!" message
  - [ ] Displays interactive form with prior life input field
  - [ ] Has "Submit" and "Cancel" buttons
  
- [ ] **Step 2:** Fill form and click "Submit" 
  - [ ] **CRITICAL:** Should process the submission (was broken before!)
  - [ ] Shows confirmation message
  - [ ] Shows public message with submitted value
  
- [ ] **Step 3:** `@bot plc`
  - [ ] Shows collected prior life responses
  - [ ] Displays proper formatting
  
- [ ] **Step 4:** Test validation
  - [ ] Submit empty form - should show error
  - [ ] Click "Cancel" - should show cancellation message

### 6. Block Action Routing Testing (Critical Fix)
- [ ] **Test 1:** Submit SimpleNameCollector form
  - [ ] Check logs for: `📞 Calling SimpleNameCollector.handle_block_action`
  - [ ] Should see: `✅ Interactive event block_actions handled by SimpleNameCollector.handle_block_action`
  
- [ ] **Test 2:** Submit MyPriorLife form
  - [ ] Check logs for: `📞 Calling SimpleNameCollector.handle_block_action` (called but returns False)
  - [ ] Check logs for: `📞 Calling MyPriorLife.handle_block_action` (called and returns True)
  - [ ] Should see: `✅ Interactive event block_actions handled by MyPriorLife.handle_block_action`
  
- [ ] **Test 3:** Both plugins work independently
  - [ ] Submit name collection form - only affects names storage
  - [ ] Submit prior life form - only affects prior life storage
  - [ ] No cross-interference between plugins

### 7. Error Handling Testing
- [ ] Network errors are handled gracefully
- [ ] Invalid inputs show proper error messages
- [ ] Plugin errors don't crash the bot
- [ ] Logs show detailed error information when issues occur

### 8. Data Persistence Testing
- [ ] Restart container: `docker restart test_bot`
- [ ] Data should persist after restart
- [ ] `@bot names_list` still shows previously collected names
- [ ] `@bot plc` still shows previously collected prior lives

## Post-Deployment Monitoring

### Monitor Logs for 24 Hours
```bash
# Watch logs in real-time
docker logs -f wrcbot_golden

# Check for errors
docker logs wrcbot_golden | grep -i error
docker logs wrcbot_golden | grep -i exception
```

### Key Success Indicators
- [ ] No error messages in logs
- [ ] Both interactive forms work end-to-end
- [ ] Data storage is functioning
- [ ] Bot remains responsive
- [ ] Memory usage is stable

## Rollback Plan
If issues are discovered:
1. Stop current container: `docker stop wrcbot_golden`
2. Start previous version: `docker run -d --name wrcbot_rollback wrcbot:0.6`
3. Investigate issues in the golden copy
4. Fix and re-test

---
**✅ All tests must pass before marking as production-ready golden copy**
