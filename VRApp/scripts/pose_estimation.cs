// Script to stream VR hand pose and button states via UDP and WebSocket

using UnityEngine;
using UnityEngine.InputSystem;
using System.Net;
using System.Net.Sockets;
using System.Text;
using WebSocketSharp;
using System.Collections;
using System.Collections.Generic;

public class OpenXR_UDPStreamer : MonoBehaviour
{
    [Header("RIGHT HAND POSITION (Input Actions)")]
    public InputActionProperty rightPosX;
    public InputActionProperty rightPosY;
    public InputActionProperty rightPosZ;

    [Header("RIGHT HAND ROTATION (Input Actions)")]
    public InputActionProperty rightRotX;
    public InputActionProperty rightRotY;
    public InputActionProperty rightRotZ;

    [Header("LEFT HAND POSITION (Input Actions)")]
    public InputActionProperty leftPosX;
    public InputActionProperty leftPosY;
    public InputActionProperty leftPosZ;

    [Header("LEFT HAND ROTATION (Input Actions)")]
    public InputActionProperty leftRotX;
    public InputActionProperty leftRotY;
    public InputActionProperty leftRotZ;

    [Header("BUTTON / TRIGGER ACTIONS")]
    public InputActionProperty rightTrigger;
    public InputActionProperty leftTrigger;
    public InputActionProperty rightPush;
    public InputActionProperty leftPush;

    [Header("BUTTON INPUTS")]
    public InputActionProperty rightButton; 
    public InputActionProperty leftButton;   

    [Header("UDP Settings")]
    public string ip = "127.0.0.1";
    public int port = 5005;

    //WebSocket
    [Header("WebSocket Settings")]
    public string wsIP = "ws://100.70.51.43:8765";   // CHANGE TO YOUR SERVER
    private WebSocket ws;
    private string latestJSON = "";

    private UdpClient client;
    private IPEndPoint endPoint;

    void Start()
    {
        client = new UdpClient();
        endPoint = new IPEndPoint(IPAddress.Parse(ip), port);

        // DO NOT CHANGE — your original enabling
        EnableAction(rightPosX); EnableAction(rightPosY); EnableAction(rightPosZ);
        EnableAction(rightRotX); EnableAction(rightRotY); EnableAction(rightRotZ);
        EnableAction(leftPosX);  EnableAction(leftPosY);  EnableAction(leftPosZ);
        EnableAction(leftRotX);  EnableAction(leftRotY);  EnableAction(leftRotZ);
        EnableAction(rightTrigger); EnableAction(leftTrigger);
        EnableAction(rightPush);    EnableAction(leftPush);
        EnableAction(rightButton);  EnableAction(leftButton);

        Debug.Log("UDP streaming started: " + ip + ":" + port);

        //WebSocket Start
        ws = new WebSocket(wsIP);
        ws.ConnectAsync();
        StartCoroutine(SendWebSocketHeartbeat()); // <-- Sends JSON at 30fps
        Debug.Log("WebSocket heartbeat initialized → " + wsIP);
    }

    void EnableAction(InputActionProperty actionProp)
    {
        if (actionProp.action != null)
            actionProp.action.Enable();
    }

    void Update()
    {
        // --- YOUR ORIGINAL READS (UNCHANGED) ---
       Vector3 rightPos = rightPosX.action.ReadValue<Vector3>();
        float rpx = rightPos.x;
        float rpy = rightPos.y;
        float rpz = rightPos.z;
       
        float rrx = rightRotX.action.ReadValue<float>();
        float rry = rightRotY.action.ReadValue<float>();
        float rrz = rightRotZ.action.ReadValue<float>();

        Vector3 leftPos = leftPosX.action.ReadValue<Vector3>();
        float lpx = leftPos.x;
        float lpy = leftPos.y;
        float lpz = leftPos.z;

        float lrx = leftRotX.action.ReadValue<float>();
        float lry = leftRotY.action.ReadValue<float>();
        float lrz = leftRotZ.action.ReadValue<float>();

        float RTrig = rightTrigger.action.ReadValue<float>();
        float LTrig = leftTrigger.action.ReadValue<float>();
        float RPush = rightPush.action.ReadValue<float>();
        float LPush = leftPush.action.ReadValue<float>();

        bool RBtn = rightButton.action.ReadValue<float>() > 0.5f; 
        bool LBtn = leftButton.action.ReadValue<float>() > 0.5f; 

        Debug.Log("Right Hand X: " + rpx);
        // --- JSON (UNCHANGED) ---
        string msg = $@"
       

{{
  ""right"": {{
    ""pos"": [{rpx}, {rpy}, {rpz}],
    ""rot"": [{rrx}, {rry}, {rrz}],
    ""trigger"": {RTrig},
    ""push"": {RPush},
    ""button""  : {RBtn}
  }},
  ""left"": {{
    ""pos"": [{lpx}, {lpy}, {lpz}],
    ""rot"": [{lrx}, {lry}, {lrz}],
    ""trigger"": {LTrig},
    ""push"": {LPush},
    ""button""  : {LBtn}
  }}
}}";

        // --- UDP send (original) ---
        byte[] data = Encoding.UTF8.GetBytes(msg);
        client.Send(data, data.Length, endPoint);
        Debug.Log(msg);

        // Save JSON so WebSocket coroutine can send it
        latestJSON = msg;
    }

    IEnumerator SendWebSocketHeartbeat()
    {
        while (ws == null || !ws.IsAlive) yield return null;

        while (true)
        {
            if (ws.IsAlive && latestJSON.Length > 5)
            {
                ws.Send(latestJSON);
                Debug.Log("WebSocket TX → JSON sent in heartbeat");
            }
            yield return new WaitForSeconds(1f/30f); // 30fps
        }
    }

    void OnDestroy()
    {
        client?.Close();
        ws?.Close();
    }
}
