#!/usr/bin/env python3
"""
Test script to understand and debug reply detection logic.
This helps understand how Slack structures messages and threads.
"""

def analyze_message_structure(message_data):
    """
    Analyze a message's structure to determine if it's a reply or root message.
    """
    print(f"\n=== Message Analysis ===")
    print(f"Message timestamp: {message_data.get('ts', 'N/A')}")
    print(f"Thread timestamp: {message_data.get('thread_ts', 'N/A')}")
    print(f"Text preview: {message_data.get('text', 'N/A')[:100]}...")
    
    # Apply the same logic as our plugin
    msg_ts = message_data.get('ts')
    thread_ts = message_data.get('thread_ts')
    
    if thread_ts and thread_ts != msg_ts:
        print(f"✅ REPLY: thread_ts ({thread_ts}) != message ts ({msg_ts})")
        return True
    else:
        print(f"❌ ROOT: No thread_ts or thread_ts == message ts")
        return False

def main():
    print("🔍 Reply Detection Logic Tester")
    print("===============================")
    
    # Test case 1: Root message (no thread_ts)
    print("\n📝 Test Case 1: Root message with no thread")
    root_message_no_thread = {
        "ts": "1234567890.123456",
        "text": "This is a root message with no replies"
    }
    analyze_message_structure(root_message_no_thread)
    
    # Test case 2: Root message that started a thread (thread_ts == ts)
    print("\n📝 Test Case 2: Root message that started a thread")
    root_message_with_thread = {
        "ts": "1234567890.123456",
        "thread_ts": "1234567890.123456",
        "text": "This is a root message that has replies",
        "reply_count": 3
    }
    analyze_message_structure(root_message_with_thread)
    
    # Test case 3: Reply message (thread_ts != ts)
    print("\n📝 Test Case 3: Reply message in a thread")
    reply_message = {
        "ts": "1234567890.789012",
        "thread_ts": "1234567890.123456",
        "text": "This is a reply to the root message"
    }
    analyze_message_structure(reply_message)
    
    # Test case 4: Another reply message
    print("\n📝 Test Case 4: Another reply message")
    another_reply = {
        "ts": "1234567890.999999",
        "thread_ts": "1234567890.123456",
        "text": "This is another reply in the same thread"
    }
    analyze_message_structure(another_reply)
    
    print("\n🎯 Key Insights:")
    print("1. Root messages either have NO thread_ts OR thread_ts == ts")
    print("2. Reply messages ALWAYS have thread_ts != ts")
    print("3. The thread_ts points to the timestamp of the root message")
    print("4. Our simplified logic should work reliably with this understanding")

if __name__ == "__main__":
    main()
